"""
知乎 Agent 系统 - 选题引擎 (Researcher)
"""
import asyncio
import json
from datetime import datetime
from typing import List, Optional
from dataclasses import asdict

from .models import Account, Topic, AccountRole


class TopicScorer:
    """选题评分器"""
    
    WEIGHTS = {
        "traffic_potential": 0.25,
        "monetization_value": 0.20,
        "evidence_availability": 0.20,
        "human_scenario_fit": 0.15,
        "risk_compatibility": 0.10,
        "competition_level": 0.10,  # 反向：竞争越小分越高
    }
    
    def score(self, topic: Topic, account: Account) -> Topic:
        """综合评分"""
        # 计算各维度分数
        topic.traffic_potential = self._calc_traffic(topic)
        topic.monetization_value = self._calc_monetization(topic, account)
        topic.evidence_availability = self._calc_evidence(topic)
        topic.human_scenario_fit = self._calc_human_fit(topic, account)
        topic.risk_compatibility = self._calc_risk(topic, account)
        topic.competition_level = self._calc_competition(topic)
        
        # 加权总分
        topic.score = sum(
            getattr(topic, k) * self.WEIGHTS[k]
            for k in self.WEIGHTS
        )
        
        return topic
    
    def _calc_traffic(self, topic: Topic) -> float:
        """流量潜力评分 (0-10)"""
        score = 0.0
        
        # 热度
        if topic.heat >= 1000000:
            score += 4.0
        elif topic.heat >= 500000:
            score += 3.0
        elif topic.heat >= 100000:
            score += 2.0
        else:
            score += 1.0
        
        # 浏览量
        if topic.views >= 500000:
            score += 3.0
        elif topic.views >= 100000:
            score += 2.0
        else:
            score += 1.0
        
        # 关注者
        if topic.followers >= 200:
            score += 3.0
        elif topic.followers >= 100:
            score += 2.0
        else:
            score += 1.0
        
        return min(score, 10.0)
    
    def _calc_monetization(self, topic: Topic, account: Account) -> float:
        """变现价值评分 (0-10)"""
        score = 5.0  # 基础分
        
        # 账号角色匹配
        if account.role == AccountRole.AI_GOODS:
            # AI/程序员领域变现加分
            ai_keywords = ["AI", "编程", "工具", "Cursor", "DeepSeek", "GPT", "开发"]
            if any(kw in topic.title for kw in ai_keywords):
                score += 3.0
            
            # 好物带货场景
            buy_keywords = ["推荐", "选择", "值得买", "对比", "评测", "价格"]
            if any(kw in topic.title for kw in buy_keywords):
                score += 2.0
        
        elif account.role == AccountRole.SALT_STORY:
            # 故事/悬疑领域
            story_keywords = ["灵异", "悬疑", "细思极恐", "经历", "故事"]
            if any(kw in topic.title for kw in story_keywords):
                score += 4.0
        
        return min(score, 10.0)
    
    def _calc_evidence(self, topic: Topic) -> float:
        """证据可得性评分 (0-10)"""
        # 基于问题类型判断是否容易获取证据
        evidence_friendly = ["评测", "体验", "实测", "对比", "使用", "价格"]
        if any(kw in topic.title for kw in evidence_friendly):
            return 8.0
        
        # 热点话题证据较难
        if topic.heat >= 500000:
            return 5.0
        
        return 6.0
    
    def _calc_human_fit(self, topic: Topic, account: Account) -> float:
        """真人场景天然性 (0-10)"""
        # 个人体验类问题天然适合真人回答
        personal_keywords = ["你", "我", "经历", "体验", "感受", "怎么看"]
        if any(kw in topic.title for kw in personal_keywords):
            return 8.0
        
        # 百科类问题真人感较弱
        wiki_keywords = ["是什么", "有哪些", "什么是"]
        if any(kw in topic.title for kw in wiki_keywords):
            return 4.0
        
        return 6.0
    
    def _calc_risk(self, topic: Topic, account: Account) -> float:
        """风控适配度 (0-10)"""
        # 恢复期账号降低评分
        if account.is_recovery_mode():
            return 5.0
        
        # 敏感话题降分
        sensitive = ["政治", "宗教", "色情", "暴力"]
        if any(kw in topic.title for kw in sensitive):
            return 2.0
        
        return 8.0
    
    def _calc_competition(self, topic: Topic) -> float:
        """竞争程度评分 (0-10, 竞争越小分越高)"""
        if topic.answers_count <= 20:
            return 9.0
        elif topic.answers_count <= 50:
            return 7.0
        elif topic.answers_count <= 100:
            return 5.0
        elif topic.answers_count <= 200:
            return 3.0
        else:
            return 2.0


class ResearcherAgent:
    """选题引擎"""
    
    def __init__(self, accounts: List[Account]):
        self.accounts = accounts
        self.scorer = TopicScorer()
    
    async def scan_hot_topics(self) -> List[Topic]:
        """扫描热榜"""
        # TODO: 实现知乎热榜爬取
        # 这里返回示例数据
        return [
            Topic(
                url="https://www.zhihu.com/question/example1",
                title="如何评价 DeepSeek V4 Pro 的性价比？",
                heat=9380000,
                answers_count=131,
                followers=449,
                views=1709525,
                domain="AI/科技",
            ),
            Topic(
                url="https://www.zhihu.com/question/example2",
                title="程序员有哪些必备的效率工具？",
                heat=560000,
                answers_count=88,
                followers=230,
                views=890000,
                domain="编程/效率",
            ),
        ]
    
    async def scan_long_tail_topics(self) -> List[Topic]:
        """扫描长尾问题"""
        # TODO: 实现长尾问题发现
        return []
    
    async def score_and_rank(self, topics: List[Topic], account: Account) -> List[Topic]:
        """评分并排序"""
        scored = [self.scorer.score(t, account) for t in topics]
        return sorted(scored, key=lambda t: t.score, reverse=True)
    
    async def generate_recommendations(self, account: Account, top_n: int = 3) -> List[Topic]:
        """生成选题推荐"""
        # 扫描所有来源
        hot_topics = await self.scan_hot_topics()
        long_tail = await self.scan_long_tail_topics()
        all_topics = hot_topics + long_tail
        
        # 评分排序
        ranked = await self.score_and_rank(all_topics, account)
        
        # 过滤低分
        qualified = [t for t in ranked if t.score >= 7.0]
        
        # 生成推荐结论
        for topic in qualified[:top_n]:
            if topic.score >= 8.5:
                topic.recommendation = "推荐"
                topic.reason = "高分选题，建议优先处理"
            elif topic.score >= 7.5:
                topic.recommendation = "可做但谨慎"
                topic.reason = "中等偏上，需注意风控"
            else:
                topic.recommendation = "可做但谨慎"
                topic.reason = "刚过线，需要强证据支撑"
        
        return qualified[:top_n]
    
    async def run(self) -> dict:
        """运行选题引擎"""
        results = {}
        
        for account in self.accounts:
            if not account.can_publish():
                continue
            
            recommendations = await self.generate_recommendations(account)
            results[account.key] = {
                "account": account.name,
                "role": account.role.value,
                "recommendations": [asdict(t) for t in recommendations],
                "generated_at": datetime.now().isoformat(),
            }
        
        return results


# 使用示例
async def main():
    # 加载账号配置
    accounts = [
        Account(
            key="zhihu-l4",
            name="不要开学秦小鱼",
            level=AccountLevel.L4,
            role=AccountRole.AI_GOODS,
            browser_profile="/Users/daxian/.openclaw/browser/zhihu-l4",
            cdp_port=18804,
            domains=["AI工具", "程序员效率", "数码硬件"],
        ),
        Account(
            key="zhihu-l6",
            name="沐晨",
            level=AccountLevel.L6,
            role=AccountRole.SALT_STORY,
            browser_profile="/Users/daxian/.openclaw/browser/zhihu-l6",
            cdp_port=18806,
            domains=["盐言故事", "悬疑", "灵异"],
        ),
    ]
    
    researcher = ResearcherAgent(accounts)
    results = await researcher.run()
    
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
