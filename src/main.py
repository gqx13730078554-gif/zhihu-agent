"""
知乎 Agent 系统 - 主入口

核心流程：
1. 选题 → 2. 生成 → 3. 辩论审查 → 4. 风控 → 5. 等待用户确认 → 6. 发布
   ↑ 存在问题则回到 3 重新辩论 ←──────────────────────────────────────┘
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .models import Account, AccountLevel, AccountRole, Content, ContentStatus, RiskState
from .researcher import ResearcherAgent
from .advanced_content_generator import AdvancedContentGenerator
from .debate_engine import DebateEngine
from .safety_gate import SafetyGate
from .publisher import PublishingScheduler
from .operator import InteractionEngine, RevenueTracker


# 待确认内容存储路径
PENDING_FILE = Path("data/pending_contents.json")


class ZhihuAgentSystem:
    """知乎 Agent 系统主类"""
    
    def __init__(self, config_path: str = "config/accounts.yaml"):
        self.config_path = Path(config_path)
        self.accounts: List[Account] = []
        self.contents: List[Content] = []
        
        # 初始化各模块
        self.researcher: ResearcherAgent = None
        self.safety_gate: SafetyGate = None
        self.publisher: PublishingScheduler = None
        self.operator: InteractionEngine = None
        self.revenue_tracker: RevenueTracker = None
    
    async def initialize(self):
        """初始化系统"""
        print("🚀 初始化知乎 Agent 系统...")
        
        # 加载账号配置
        self.accounts = await self._load_accounts()
        print(f"✅ 加载 {len(self.accounts)} 个账号")
        
        # 初始化各模块
        self.researcher = ResearcherAgent(self.accounts)
        self.content_generator = AdvancedContentGenerator()
        self.debate_engine = DebateEngine(max_rounds=3)
        self.safety_gate = SafetyGate()
        self.publisher = PublishingScheduler(self.accounts)
        self.operator = InteractionEngine(self.accounts)
        self.revenue_tracker = RevenueTracker()
        
        print("✅ 系统初始化完成")
    
    async def _load_accounts(self) -> List[Account]:
        """加载账号配置"""
        # TODO: 从配置文件加载
        # 这里返回示例配置
        return [
            Account(
                key="zhihu-l4",
                name="不要开学秦小鱼",
                level=AccountLevel.L4,
                role=AccountRole.AI_GOODS,
                browser_profile="/Users/daxian/.openclaw/browser/zhihu-l4",
                cdp_port=18804,
                risk_state=RiskState.NORMAL,
                creation_score=1885,
                domains=["AI工具", "程序员效率", "数码硬件", "云服务"],
                monetization_paths=["好物推荐佣金", "AI工具订阅", "内容自荐"],
            ),
            Account(
                key="zhihu-l6",
                name="沐晨",
                level=AccountLevel.L6,
                role=AccountRole.SALT_STORY,
                browser_profile="/Users/daxian/.openclaw/browser/zhihu-l6",
                cdp_port=18806,
                risk_state=RiskState.NORMAL,
                creation_score=25723,
                domains=["盐言故事", "悬疑", "灵异"],
                monetization_paths=["盐言投稿", "内容自荐", "故事热点"],
            ),
        ]
    
    async def run_daily_pipeline(self):
        """运行日常流水线（生成 → 辩论 → 风控 → 等待确认）
        
        核心约束：生成后不自动发布，必须等待用户确认。
        存在问题则重新辩论，直到通过风控。
        """
        print("\n" + "="*60)
        print(f"📅 开始日常流水线 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*60)
        
        # Step 1: 选题
        print("\n📋 Step 1: 选题引擎")
        topic_recommendations = await self.researcher.run()
        print(f"✅ 生成 {sum(len(v['recommendations']) for v in topic_recommendations.values())} 个选题推荐")
        
        # Step 2: 写作 + 辩论审查
        print("\n✍️  Step 2: 内容工厂 + 辩论审查")
        drafts = await self._generate_drafts(topic_recommendations)
        print(f"✅ 生成 {len(drafts)} 篇内容草稿")
        
        # Step 3: 风控检查（不通过则重新辩论）
        print("\n🛡️  Step 3: 风控闸门")
        final_drafts = await self._safety_check_with_retry(drafts)
        
        # Step 4: 保存到待确认队列（不发布！）
        print("\n⏸️  Step 4: 保存到待确认队列")
        self._save_pending(final_drafts)
        print(f"⏸️  {len(final_drafts)} 篇内容等待用户确认")
        print("   ⚠️  不会自动发布，等待用户确认后执行 publish_confirmed()")
        
        print("\n" + "="*60)
        print("✅ 日常流水线完成（等待确认阶段）")
        print("="*60)
        
        return final_drafts
    
    async def _safety_check_with_retry(
        self, drafts: List[Content], max_retries: int = 3
    ) -> List[Content]:
        """风控检查 + 不通过则重新辩论（最多重试max_retries次）"""
        final = []
        
        for content in drafts:
            account = next(a for a in self.accounts if a.key == content.account_key)
            
            for attempt in range(max_retries + 1):
                result = self.safety_gate.check(content, account)
                
                if result.passed:
                    content.status = ContentStatus.PENDING_REVIEW
                    final.append(content)
                    print(f"  ✅ {content.title[:30]}... (得分: {result.score:.1f})")
                    break
                
                # 不通过 → 重新辩论
                if attempt < max_retries:
                    print(f"  🔄 {content.title[:30]}... 风控未过({result.score:.1f})，第{attempt+1}次重新辩论")
                    debate_result = self.debate_engine.debate(content.body)
                    content.body = debate_result["improved_content"]
                    content.debate_history += "\n--- 重新辩论 ---\n" + debate_result["debate_state"].history
                    content.debate_verdict = debate_result["verdict"]
                else:
                    # 超过重试次数，标记为拒绝
                    content.status = ContentStatus.REJECTED
                    print(f"  ❌ {content.title[:30]}... 风控未过({result.score:.1f})，已放弃")
                    for issue in result.issues:
                        print(f"     - {issue}")
        
        return final
    
    def _save_pending(self, drafts: List[Content]):
        """保存待确认内容到文件"""
        PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        pending_data = []
        for content in drafts:
            pending_data.append({
                "id": content.id,
                "account_key": content.account_key,
                "topic": content.topic.title if content.topic else "",
                "title": content.title,
                "body": content.body,
                "word_count": content.word_count,
                "risk_score": content.risk_score,
                "debate_verdict": content.debate_verdict,
                "created_at": datetime.now().isoformat(),
            })
        
        PENDING_FILE.write_text(json.dumps(pending_data, ensure_ascii=False, indent=2))
        print(f"  💾 已保存到 {PENDING_FILE}")
    
    async def publish_confirmed(self) -> List[Content]:
        """用户确认后发布待确认内容
        
        调用方式：用户回复"发布"后触发此方法
        """
        if not PENDING_FILE.exists():
            print("⚠️ 没有待确认的内容")
            return []
        
        # 读取待确认内容
        pending_data = json.loads(PENDING_FILE.read_text())
        if not pending_data:
            print("⚠️ 待确认队列为空")
            return []
        
        print(f"\n📤 用户确认发布 {len(pending_data)} 篇内容")
        
        # 重建Content对象
        confirmed_contents = []
        for data in pending_data:
            account = next((a for a in self.accounts if a.key == data["account_key"]), None)
            if not account:
                continue
            
            content = Content(
                id=data["id"],
                account_key=data["account_key"],
                topic=None,
                content_type="answer",
                title=data["title"],
                body=data["body"],
                word_count=data["word_count"],
            )
            content.status = ContentStatus.APPROVED
            confirmed_contents.append(content)
        
        # 发布
        print("\n📤 发布调度")
        publish_plans = await self.publisher.run(confirmed_contents)
        print(f"✅ 完成 {len(publish_plans)} 篇发布")
        
        # 清空待确认队列
        PENDING_FILE.write_text("[]")
        print("🗑️ 待确认队列已清空")
        
        return confirmed_contents
    
    async def reject_and_rework(self, content_ids: Optional[List[str]] = None):
        """拒绝指定内容并触发重新辩论
        
        如果content_ids为None，拒绝所有待确认内容
        """
        if not PENDING_FILE.exists():
            print("⚠️ 没有待确认的内容")
            return
        
        pending_data = json.loads(PENDING_FILE.read_text())
        
        if content_ids is None:
            # 拒绝全部
            rejected = pending_data
            remaining = []
        else:
            rejected = [d for d in pending_data if d["id"] in content_ids]
            remaining = [d for d in pending_data if d["id"] not in content_ids]
        
        print(f"\n🔄 拒绝 {len(rejected)} 篇内容，触发重新辩论")
        
        # 重新辩论
        reworked = []
        for data in rejected:
            account = next((a for a in self.accounts if a.key == data["account_key"]), None)
            if not account:
                continue
            
            content = Content(
                id=data["id"],
                account_key=data["account_key"],
                topic=None,
                content_type="answer",
                title=data["title"],
                body=data["body"],
                word_count=data["word_count"],
            )
            
            # 重新辩论
            debate_result = self.debate_engine.debate(content.body)
            content.body = debate_result["improved_content"]
            content.debate_history = debate_result["debate_state"].history
            content.debate_verdict = debate_result["verdict"]
            content.status = ContentStatus.PENDING_REVIEW
            reworked.append(content)
            print(f"  🔄 重新辩论: {content.title[:30]}...")
        
        # 风控检查
        if reworked:
            final = await self._safety_check_with_retry(reworked)
            # 合并到待确认队列
            remaining_data = remaining
            for content in final:
                remaining_data.append({
                    "id": content.id,
                    "account_key": content.account_key,
                    "topic": "",
                    "title": content.title,
                    "body": content.body,
                    "word_count": content.word_count,
                    "risk_score": content.risk_score,
                    "debate_verdict": content.debate_verdict,
                    "created_at": datetime.now().isoformat(),
                })
            PENDING_FILE.write_text(json.dumps(remaining_data, ensure_ascii=False, indent=2))
            print(f"✅ {len(final)} 篇重新辩论完成，已更新待确认队列")
    
    async def _generate_drafts(self, topic_recommendations: dict) -> List[Content]:
        """生成内容草稿（使用高级内容生成器）"""
        from .models import Topic
        
        drafts = []
        
        for account_key, data in topic_recommendations.items():
            account = next((a for a in self.accounts if a.key == account_key), None)
            if not account:
                continue
            
            for topic_data in data["recommendations"][:2]:  # 每个账号最多2篇
                # 创建Topic对象
                topic = Topic(
                    url=topic_data.get("url", "https://www.zhihu.com/question/mock"),
                    title=topic_data["title"],
                    heat=topic_data.get("heat", 1000000),
                    answers_count=topic_data.get("answers_count", 100),
                    followers=topic_data.get("followers", 200),
                    views=topic_data.get("views", 500000),
                    domain=topic_data.get("domain", "AI/科技"),
                    score=topic_data.get("score", 8.0),
                )
                
                # 使用高级内容生成器（内置风格学习+释义+多样性）
                content = self.content_generator.generate_content(topic, account)
                
                # 辩论式质量审查（借鉴TradingAgents的bull vs bear机制）
                debate_result = self.debate_engine.debate(content.body)
                content.body = debate_result["improved_content"]
                content.debate_history = debate_result["debate_state"].history
                content.debate_verdict = debate_result["verdict"]
                
                content.status = ContentStatus.PENDING_REVIEW
                drafts.append(content)
                print(f"  ✅ 生成内容: {content.title[:40]}... ({content.word_count}字) [{debate_result['verdict']}]")
        
        return drafts
    
    def _generate_mock_content(self, title: str, account_key: str) -> str:
        """生成模拟内容"""
        if account_key == "zhihu-l4":
            return f"""
我直接说结论：这个问题值得认真回答。

作为一个用了3年相关工具的程序员，我来分享一下真实体验。

## 我的使用场景

我主要负责后端开发，日常需要处理大量代码审查和文档编写工作。之前试过不少工具，踩了不少坑。

## 实测体验

上周我花了一整天时间做了个对比测试：

- 工具A：响应速度快，但代码质量一般
- 工具B：代码质量高，但价格贵（每月¥99）
- 工具C：性价比高，适合新手

实测下来，我觉得对于大多数程序员来说，工具C是最优解。原因很简单：
1. 价格只有工具B的1/3
2. 核心功能覆盖90%的使用场景
3. 学习成本低，上手快

## 不推荐人群

如果你是大厂员工，公司有预算，直接用工具B，体验更好。
如果你是学生或者刚入行，工具C完全够用，别花冤枉钱。

## 购买建议

现在工具C官网有活动，年付打7折，算下来每月只要¥28。
链接我放评论区，需要的自取。
"""
        else:
            return f"""
那天晚上发生的事，我到现在都想不明白。

我叫李明，在老家镇上开了一家小卖部。生意不大，但勉强够糊口。

那天是农历七月十五，中元节。

晚上十点多，我正在盘点库存，突然听到门外有敲门声。

"咚咚咚"

这么晚了，会是谁呢？

我打开门，外面站着一个穿白衣服的女人。她低着头，长发遮住了脸。

"买东西吗？"我问。

她没说话，只是递过来一张百元大钞。

我接过钱，正准备找零，突然发现不对劲——

那张钱，是湿的。
"""


async def main():
    """主函数"""
    system = ZhihuAgentSystem()
    await system.initialize()
    await system.run_daily_pipeline()


if __name__ == "__main__":
    asyncio.run(main())
