"""
知乎 Agent 系统 - 发布调度 (Publisher)
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass

from .models import Account, Content, ContentStatus


@dataclass
class PublishSlot:
    """发布时段"""
    name: str
    start_hour: int
    start_minute: int
    end_hour: int
    end_minute: int


# 最佳发布时段
OPTIMAL_WINDOWS = {
    "morning": PublishSlot("早高峰", 10, 0, 12, 0),
    "noon": PublishSlot("午休", 12, 0, 13, 30),
    "evening": PublishSlot("晚高峰", 19, 0, 21, 0),
}


@dataclass
class PublishPlan:
    """发布计划"""
    account_key: str
    content: Content
    scheduled_time: datetime
    slot_name: str
    priority: int  # 1-10, 越高越优先


class PublishingScheduler:
    """发布调度器"""
    
    # 账号发布配额
    QUOTAS = {
        "L3": {"answers": 2, "ideas": 1, "articles": 1},
        "L4": {"answers": 2, "ideas": 1, "articles": 1},
        "L5": {"answers": 3, "ideas": 2, "articles": 2},
        "L6": {"answers": 3, "ideas": 2, "articles": 2},
    }
    
    # 防关联规则
    ANTI_CORRELATION = {
        "same_topic_gap_hours": 48,       # 同话题间隔48小时
        "cross_account_gap_minutes": 30,  # 跨账号间隔30分钟
        "no_cross_like": True,            # 禁止互赞
        "no_cross_comment": True,         # 禁止互评
    }
    
    def __init__(self, accounts: List[Account]):
        self.accounts = {a.key: a for a in accounts}
        self.publish_history: List[PublishPlan] = []
    
    def get_quota(self, account: Account, content_type: str) -> int:
        """获取账号发布配额"""
        level_key = f"L{account.level.value}"
        # Normalize: "answer" -> "answers"
        plural = content_type + "s" if not content_type.endswith("s") else content_type
        return self.QUOTAS.get(level_key, {}).get(plural, 0)
    
    def get_today_publish_count(self, account: Account, content_type: str) -> int:
        """获取今日已发布数量"""
        today = datetime.now().date()
        count = 0
        
        for plan in self.publish_history:
            if (plan.account_key == account.key and 
                plan.content.content_type == content_type and
                plan.scheduled_time.date() == today and
                plan.content.status == ContentStatus.PUBLISHED):
                count += 1
        
        return count
    
    def can_publish(self, account: Account, content: Content) -> tuple[bool, str]:
        """检查是否可以发布"""
        # 检查账号状态
        if not account.can_publish():
            return False, f"账号处于 {account.risk_state.value} 状态，禁止发布"
        
        # 检查配额
        quota = self.get_quota(account, content.content_type)
        published = self.get_today_publish_count(account, content.content_type)
        
        if published >= quota:
            return False, f"今日 {content.content_type} 发布已达上限 ({published}/{quota})"
        
        # 检查防关联
        if not self._check_anti_correlation(account, content):
            return False, "触发防关联规则，请稍后再试"
        
        return True, "可以发布"
    
    def _check_anti_correlation(self, account: Account, content: Content) -> bool:
        """检查防关联规则"""
        now = datetime.now()
        
        # 检查同话题间隔
        for plan in self.publish_history:
            if plan.content.topic.url == content.topic.url:
                gap = now - plan.scheduled_time
                if gap < timedelta(hours=self.ANTI_CORRELATION["same_topic_gap_hours"]):
                    return False
        
        # 检查跨账号间隔
        for plan in self.publish_history:
            if plan.account_key != account.key:
                gap = now - plan.scheduled_time
                if gap < timedelta(minutes=self.ANTI_CORRELATION["cross_account_gap_minutes"]):
                    return False
        
        return True
    
    def suggest_publish_time(self, account: Account, content: Content) -> datetime:
        """建议发布时间"""
        now = datetime.now()
        
        # 根据内容类型和账号选择时段
        if content.content_type == "answer":
            # 回答优先早高峰或晚高峰
            if now.hour < 10:
                return now.replace(hour=10, minute=30, second=0)
            elif now.hour < 19:
                return now.replace(hour=19, minute=0, second=0)
            else:
                # 明天早高峰
                tomorrow = now + timedelta(days=1)
                return tomorrow.replace(hour=10, minute=30, second=0)
        
        elif content.content_type == "article":
            # 文章优先晚高峰
            if now.hour < 19:
                return now.replace(hour=19, minute=30, second=0)
            else:
                tomorrow = now + timedelta(days=1)
                return tomorrow.replace(hour=19, minute=30, second=0)
        
        else:
            # 想法随时可以发
            return now + timedelta(minutes=30)
    
    def create_publish_plan(self, account: Account, content: Content) -> PublishPlan:
        """创建发布计划"""
        scheduled_time = self.suggest_publish_time(account, content)
        
        # 确定优先级
        priority = int(content.topic.score) if content.topic.score else 5
        
        plan = PublishPlan(
            account_key=account.key,
            content=content,
            scheduled_time=scheduled_time,
            slot_name=self._get_slot_name(scheduled_time),
            priority=priority,
        )
        
        self.publish_history.append(plan)
        return plan
    
    def _get_slot_name(self, dt: datetime) -> str:
        """获取时段名称"""
        hour = dt.hour
        
        if 10 <= hour < 12:
            return "早高峰"
        elif 12 <= hour < 14:
            return "午休"
        elif 19 <= hour < 21:
            return "晚高峰"
        else:
            return "其他时段"
    
    async def execute_publish(self, plan: PublishPlan) -> bool:
        """执行发布"""
        # TODO: 实现浏览器自动化发布
        # 这里只是模拟
        
        account = self.accounts[plan.account_key]
        
        # 检查是否可以发布
        can_publish, reason = self.can_publish(account, plan.content)
        if not can_publish:
            print(f"❌ 无法发布: {reason}")
            return False
        
        # 模拟发布过程
        print(f"📝 正在发布到 {account.name}...")
        print(f"   标题: {plan.content.title}")
        print(f"   时段: {plan.slot_name}")
        
        # 模拟浏览器操作
        await asyncio.sleep(1)
        
        # 更新状态
        plan.content.status = ContentStatus.PUBLISHED
        plan.content.published_at = datetime.now()
        plan.content.published_url = f"https://www.zhihu.com/question/xxx/answer/{plan.content.id}"
        
        print(f"✅ 发布成功: {plan.content.published_url}")
        
        return True
    
    async def run(self, pending_contents: List[Content]) -> List[PublishPlan]:
        """运行发布调度"""
        plans = []
        
        for content in pending_contents:
            if content.status != ContentStatus.APPROVED:
                continue
            
            account = self.accounts.get(content.account_key)
            if not account:
                continue
            
            plan = self.create_publish_plan(account, content)
            plans.append(plan)
        
        # 按时间排序执行
        plans.sort(key=lambda p: p.scheduled_time)
        
        for plan in plans:
            # 等待到计划时间
            now = datetime.now()
            if plan.scheduled_time > now:
                wait_seconds = (plan.scheduled_time - now).total_seconds()
                print(f"⏰ 等待 {wait_seconds:.0f} 秒后发布...")
                await asyncio.sleep(min(wait_seconds, 5))  # 演示用，最多等5秒
            
            await self.execute_publish(plan)
        
        return plans


class ColdStartEngine:
    """冷启动引擎 - 发布后互动"""
    
    def __init__(self, browser):
        self.browser = browser
    
    async def run_cold_start(self, content: Content, account: Account):
        """执行冷启动"""
        print(f"🔄 开始冷启动: {content.title}")
        
        # 发布后45分钟开始
        await asyncio.sleep(5)  # 演示用
        
        # 自然浏览行为
        await self._natural_browsing(account)
        
        # 相关话题浏览
        await self._related_topic_browsing(account, content)
        
        print(f"✅ 冷启动完成")
    
    async def _natural_browsing(self, account: Account):
        """自然浏览行为"""
        # TODO: 实现自然浏览
        pass
    
    async def _related_topic_browsing(self, account: Account, content: Content):
        """相关话题浏览"""
        # TODO: 实现相关话题浏览
        pass
