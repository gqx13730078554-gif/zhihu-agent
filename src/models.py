"""
知乎 Agent 系统 - 核心数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict


class AccountLevel(Enum):
    L3 = 3
    L4 = 4
    L5 = 5
    L6 = 6


class AccountRole(Enum):
    AI_GOODS = "ai_programmer_goods"      # L4: AI/程序员好物
    SALT_STORY = "salt_story_suspense"    # L6: 盐言故事


class RiskState(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    RECOVERY = "recovery"
    SUSPENDED = "suspended"


class ContentStatus(Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    FOLDED = "folded"


@dataclass
class Account:
    """账号配置"""
    key: str                              # zhihu-l4 / zhihu-l6
    name: str                             # 不要开学秦小鱼 / 沐晨
    level: AccountLevel
    role: AccountRole
    browser_profile: str
    cdp_port: int
    risk_state: RiskState = RiskState.NORMAL
    creation_score: int = 0
    folded_count: int = 0
    
    # 变现权益
    goods_recommendation_enabled: bool = False
    content_recommendation_quota: int = 0
    brand_tasks_enabled: bool = False
    salt_author_enabled: bool = False
    
    # 领域匹配
    domains: List[str] = field(default_factory=list)
    monetization_paths: List[str] = field(default_factory=list)
    
    def can_publish(self) -> bool:
        """是否可以发布"""
        return self.risk_state in (RiskState.NORMAL, RiskState.WARNING)
    
    def is_recovery_mode(self) -> bool:
        """是否处于恢复期"""
        return self.risk_state == RiskState.RECOVERY


@dataclass
class Topic:
    """选题"""
    url: str
    title: str
    heat: int                             # 热度
    answers_count: int
    followers: int
    views: int
    domain: str
    
    # 评分维度
    score: float = 0.0
    traffic_potential: float = 0.0
    monetization_value: float = 0.0
    evidence_availability: float = 0.0
    human_scenario_fit: float = 0.0
    risk_compatibility: float = 0.0
    competition_level: float = 0.0
    
    # 竞品样本
    competitor_samples: List[Dict] = field(default_factory=list)
    
    # 推荐结论
    recommendation: str = ""              # 推荐 / 可做但谨慎 / 不建议
    reason: str = ""


@dataclass
class Product:
    """好物推荐商品"""
    name: str
    category: str
    commission_rate: float                # 佣金比例 0.1 - 0.3
    price: float
    url: str
    relevance_score: float = 0.0          # 与内容的相关度


@dataclass
class Content:
    """内容"""
    id: str
    account_key: str
    topic: Topic
    content_type: str                     # answer / article / idea
    title: str
    body: str
    word_count: int
    
    # 反AI检测
    ai_label: bool = False
    anti_ai_checks: Dict[str, bool] = field(default_factory=dict)
    anti_ai_score: float = 0.0
    
    # 辩论记录（借鉴TradingAgents）
    debate_history: str = ""
    debate_verdict: str = ""
    
    # 发布状态
    status: ContentStatus = ContentStatus.DRAFT
    published_at: Optional[datetime] = None
    published_url: Optional[str] = None
    
    # 数据追踪
    reads: int = 0
    upvotes: int = 0
    comments_count: int = 0
    collections: int = 0
    shares: int = 0
    
    # 变现
    products: List[Product] = field(default_factory=list)
    estimated_commission: float = 0.0
    actual_commission: float = 0.0
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    notes: str = ""


@dataclass
class SafetyCheckResult:
    """风控检查结果"""
    passed: bool
    score: float                          # 0-10
    checks: Dict[str, bool]
    issues: List[str]
    suggestions: List[str]


@dataclass
class DailyMetrics:
    """日数据"""
    date: str
    account_key: str
    
    # 发布
    contents_published: int = 0
    contents_folded: int = 0
    
    # 流量
    total_reads: int = 0
    total_upvotes: int = 0
    total_comments: int = 0
    total_collections: int = 0
    total_shares: int = 0
    
    # 收益
    commission: float = 0.0
    activity_rewards: float = 0.0
    total_earnings: float = 0.0
    
    # 风控
    ai_warnings: int = 0
    risk_state: RiskState = RiskState.NORMAL


@dataclass
class DailyReport:
    """日报"""
    date: str
    account_key: str
    
    # 数据
    metrics: DailyMetrics
    
    # 发布内容
    contents: List[Content] = field(default_factory=list)
    
    # 风控观察
    risk_observation: str = ""
    folded_details: List[Dict] = field(default_factory=list)
    
    # 收益分析
    revenue_analysis: str = ""
    
    # 明日计划
    next_day_plan: List[str] = field(default_factory=list)
    
    # 异常
    anomalies: List[str] = field(default_factory=list)
