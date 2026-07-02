"""
知乎 Agent 系统 - 主入口
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List

from .models import Account, AccountLevel, AccountRole, Content, ContentStatus, RiskState
from .researcher import ResearcherAgent
from .advanced_content_generator import AdvancedContentGenerator
from .debate_engine import DebateEngine
from .safety_gate import SafetyGate
from .publisher import PublishingScheduler
from .operator import InteractionEngine, RevenueTracker


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
        """运行日常流水线"""
        print("\n" + "="*60)
        print(f"📅 开始日常流水线 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*60)
        
        # Step 1: 选题
        print("\n📋 Step 1: 选题引擎")
        topic_recommendations = await self.researcher.run()
        print(f"✅ 生成 {sum(len(v['recommendations']) for v in topic_recommendations.values())} 个选题推荐")
        
        # Step 2: 写作（模拟）
        print("\n✍️  Step 2: 内容工厂")
        drafts = await self._generate_drafts(topic_recommendations)
        print(f"✅ 生成 {len(drafts)} 篇内容草稿")
        
        # Step 3: 风控检查
        print("\n🛡️  Step 3: 风控闸门")
        approved_contents = []
        for content in drafts:
            account = next(a for a in self.accounts if a.key == content.account_key)
            result = self.safety_gate.check(content, account)
            
            if result.passed:
                content.status = ContentStatus.APPROVED
                approved_contents.append(content)
                print(f"  ✅ {content.title[:30]}... (得分: {result.score:.1f})")
            else:
                content.status = ContentStatus.REJECTED
                print(f"  ❌ {content.title[:30]}... (得分: {result.score:.1f})")
                for issue in result.issues:
                    print(f"     - {issue}")
        
        # Step 4: 发布调度
        print("\n📤 Step 4: 发布调度")
        publish_plans = await self.publisher.run(approved_contents)
        print(f"✅ 完成 {len(publish_plans)} 篇发布")
        
        # Step 5: 互动运营
        print("\n💬 Step 5: 互动引擎")
        for account in self.accounts:
            account_contents = [c for c in approved_contents if c.account_key == account.key]
            
            # 回复评论
            for content in account_contents:
                await self.operator.reply_to_comments(content, account)
            
            # 生成日报
            report = await self.operator.generate_daily_report(account, account_contents)
            print(f"\n📊 {account.name} 日报:")
            print(f"   发布: {report.metrics.contents_published} 篇")
            print(f"   阅读: {report.metrics.total_reads}")
            print(f"   赞同: {report.metrics.total_upvotes}")
            print(f"   风控: {report.risk_observation}")
            print(f"   收益: {report.revenue_analysis}")
        
        print("\n" + "="*60)
        print("✅ 日常流水线完成")
        print("="*60)
    
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
