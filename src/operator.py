"""
知乎 Agent 系统 - 互动引擎 (Operator)
"""
import asyncio
from datetime import datetime
from typing import List, Dict
from dataclasses import dataclass

from .models import Account, Content, DailyReport, DailyMetrics


@dataclass
class Comment:
    """评论"""
    id: str
    author: str
    text: str
    created_at: datetime
    is_reply: bool = False
    reply_text: str = ""


@dataclass
class ContentMetrics:
    """内容数据"""
    content_id: str
    reads: int = 0
    upvotes: int = 0
    comments: int = 0
    collections: int = 0
    shares: int = 0
    followers_gained: int = 0


class InteractionEngine:
    """互动引擎"""
    
    # 评论回复规则
    COMMENT_RULES = {
        "min_length": 10,              # 最少10字
        "response_time_hours": 2,      # 2小时内回复
        "tone": "natural",             # 自然口吻
        "no_template": True,           # 禁止模板回复
    }
    
    def __init__(self, accounts: List[Account]):
        self.accounts = {a.key: a for a in accounts}
    
    async def fetch_new_comments(self, content: Content) -> List[Comment]:
        """获取新评论"""
        # TODO: 实现评论抓取
        # 模拟数据
        return [
            Comment(
                id="c1",
                author="用户A",
                text="写得很详细，请问这个工具在哪里下载？",
                created_at=datetime.now(),
            ),
            Comment(
                id="c2",
                author="用户B",
                text="不同意你的观点，我觉得...",
                created_at=datetime.now(),
            ),
        ]
    
    async def generate_reply(self, comment: Comment, content: Content) -> str:
        """生成回复"""
        # TODO: 接入LLM生成自然回复
        # 这里返回示例
        
        if "下载" in comment.text or "哪里" in comment.text:
            return "官网可以直接下载，我文章里有链接～"
        elif "不同意" in comment.text:
            return "理解你的观点，不过我实测下来确实是这样，可能场景不同？"
        else:
            return "感谢评论～"
    
    async def reply_to_comments(self, content: Content, account: Account):
        """回复评论"""
        comments = await self.fetch_new_comments(content)
        
        for comment in comments:
            if comment.is_reply:
                continue
            
            # 生成回复
            reply = await self.generate_reply(comment, content)
            
            # 检查回复长度
            if len(reply) < self.COMMENT_RULES["min_length"]:
                print(f"⚠️ 回复太短，跳过: {reply}")
                continue
            
            # 发布回复
            print(f"💬 回复 @{comment.author}: {reply}")
            # TODO: 实际发布回复
    
    async def track_metrics(self, content: Content) -> ContentMetrics:
        """追踪内容数据"""
        # TODO: 实现数据抓取
        # 模拟数据
        return ContentMetrics(
            content_id=content.id,
            reads=1234,
            upvotes=56,
            comments=12,
            collections=23,
            shares=5,
        )
    
    async def identify_high_potential(self, contents: List[Content]) -> List[Content]:
        """识别高潜力内容（建议自荐）"""
        high_potential = []
        
        for content in contents:
            metrics = await self.track_metrics(content)
            
            # 高潜力标准
            if metrics.reads >= 1000 and metrics.upvotes >= 50:
                high_potential.append(content)
                print(f"⭐ 高潜力内容: {content.title} (阅读{metrics.reads}, 赞同{metrics.upvotes})")
        
        return high_potential
    
    async def generate_daily_report(self, account: Account, contents: List[Content]) -> DailyReport:
        """生成日报"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 汇总数据
        total_reads = 0
        total_upvotes = 0
        total_comments = 0
        total_collections = 0
        total_shares = 0
        
        for content in contents:
            metrics = await self.track_metrics(content)
            total_reads += metrics.reads
            total_upvotes += metrics.upvotes
            total_comments += metrics.comments
            total_collections += metrics.collections
            total_shares += metrics.shares
        
        # 创建日报
        metrics = DailyMetrics(
            date=today,
            account_key=account.key,
            contents_published=len([c for c in contents if c.status.value == "published"]),
            total_reads=total_reads,
            total_upvotes=total_upvotes,
            total_comments=total_comments,
            total_collections=total_collections,
            total_shares=total_shares,
        )
        
        report = DailyReport(
            date=today,
            account_key=account.key,
            metrics=metrics,
            contents=contents,
        )
        
        # 生成分析
        report.risk_observation = self._analyze_risk(account, contents)
        report.revenue_analysis = self._analyze_revenue(contents)
        report.next_day_plan = self._generate_next_day_plan(account, contents)
        report.anomalies = self._detect_anomalies(account, contents)
        
        return report
    
    def _analyze_risk(self, account: Account, contents: List[Content]) -> str:
        """分析风控状态"""
        folded = [c for c in contents if c.status.value == "folded"]
        
        if len(folded) > 0:
            return f"⚠️ 发现 {len(folded)} 条内容被折叠，需要排查原因"
        elif account.risk_state.value == "recovery":
            return "🔄 账号处于恢复期，继续观察"
        else:
            return "✅ 风控状态正常"
    
    def _analyze_revenue(self, contents: List[Content]) -> str:
        """分析收益"""
        total_commission = sum(c.actual_commission for c in contents)
        
        if total_commission > 0:
            return f"💰 今日佣金收入: ¥{total_commission:.2f}"
        else:
            return "💰 今日无佣金收入，继续优化好物植入"
    
    def _generate_next_day_plan(self, account: Account, contents: List[Content]) -> List[str]:
        """生成明日计划"""
        plan = []
        
        # 根据今日情况生成计划
        published_count = len([c for c in contents if c.status.value == "published"])
        folded_count = len([c for c in contents if c.status.value == "folded"])
        
        if folded_count > 0:
            plan.append("P0: 排查折叠原因，调整内容策略")
        
        if published_count < 2:
            plan.append("P0: 完成今日发布配额")
        
        plan.append("P1: 监控今日内容数据")
        plan.append("P1: 回复新评论")
        plan.append("P2: 检查好物推荐点击数据")
        
        return plan
    
    def _detect_anomalies(self, account: Account, contents: List[Content]) -> List[str]:
        """检测异常"""
        anomalies = []
        
        # 检测连续零出单
        recent_contents = sorted(contents, key=lambda c: c.published_at or datetime.min, reverse=True)[:3]
        zero_commission_streak = sum(1 for c in recent_contents if c.actual_commission == 0)
        
        if zero_commission_streak >= 3:
            anomalies.append(f"连续 {zero_commission_streak} 篇内容零佣金")
        
        # 检测折叠率
        if len(contents) > 0:
            fold_rate = len([c for c in contents if c.status.value == "folded"]) / len(contents)
            if fold_rate > 0.3:
                anomalies.append(f"折叠率过高: {fold_rate:.1%}")
        
        return anomalies


class RevenueTracker:
    """收益追踪器"""
    
    CHANNELS = {
        "goods_recommendation": {
            "name": "好物推荐",
            "commission_rate_range": (0.10, 0.30),
            "best_categories": ["AI编程工具", "云服务器", "机械键盘", "编程书籍"],
        },
        "content_self_recommendation": {
            "name": "内容自荐",
            "quota_per_month": 3,
        },
        "brand_tasks": {
            "name": "芝士平台品牌任务",
        },
        "salt_story": {
            "name": "盐言故事",
        },
        "activity_rewards": {
            "name": "活动奖励",
        },
    }
    
    async def track_commission(self, content: Content) -> float:
        """追踪佣金"""
        # TODO: 接入知乎收益API
        # 这里返回模拟数据
        return content.estimated_commission
    
    async def generate_revenue_report(self, account: Account, contents: List[Content]) -> Dict:
        """生成收益报告"""
        total_commission = sum(c.actual_commission for c in contents)
        
        return {
            "account": account.name,
            "period": "today",
            "total_commission": total_commission,
            "breakdown": {
                "goods_recommendation": total_commission,  # 简化
            },
            "top_earning_contents": sorted(
                contents,
                key=lambda c: c.actual_commission,
                reverse=True
            )[:3],
        }
