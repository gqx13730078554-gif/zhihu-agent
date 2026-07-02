# 知乎 Agent 系统架构设计

> 目标：高频、安全、可持续的知乎内容发布与变现系统
> 更新时间：2026-07-02
> 基于现有矩阵策略、反AI检测规则、恢复期SOP升级

---

## 一、系统总览

```
┌─────────────────────────────────────────────────────────────────┐
│                    Zhihu Agent System                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   │
│  │ 选题引擎  │──▶│ 内容工厂  │──▶│ 风控闸门  │──▶│ 发布调度  │   │
│  │ Researcher│   │  Writer  │   │  Safety  │   │Publisher │   │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   │
│       │               │               │               │        │
│       ▼               ▼               ▼               ▼        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              数据中枢 (Data Hub)                          │  │
│  │  热榜监控 │ 竞品分析 │ 发布历史 │ 收益追踪 │ 风控日志    │  │
│  └──────────────────────────────────────────────────────────┘  │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐                   │
│  │ 互动引擎  │   │ 收益引擎  │   │ 复盘引擎  │                   │
│  │ Operator │   │ Revenue  │   │ Review   │                   │
│  └──────────┘   └──────────┘   └──────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、核心模块设计

### 2.1 选题引擎 (Researcher Agent)

#### 职责
- 扫描知乎热榜、长尾问题、搜索趋势
- 评估每个问题的：流量潜力、变现价值、证据可得性、风控适配度
- 输出带竞品样本分析的候选题

#### 数据源
```python
# 数据源配置
DATA_SOURCES = {
    "zhihu_hot": "https://www.zhihu.com/hot",           # 热榜
    "zhihu_search": "https://www.zhihu.com/search",      # 搜索趋势
    "zhihu_topics": "https://www.zhihu.com/topics",      # 话题页
    "baidu_index": "百度指数API",                         # 外部趋势
    "weibo_hot": "微博热搜",                              # 跨平台热点
    "competitor_feeds": "竞品账号RSS",                     # 竞品监控
}
```

#### 选题评分模型
```python
class TopicScorer:
    """选题评分器"""
    
    WEIGHTS = {
        "traffic_potential": 0.25,      # 流量潜力
        "monetization_value": 0.20,     # 变现价值
        "evidence_availability": 0.20,  # 证据可得性
        "human_scenario_fit": 0.15,     # 真人场景天然性
        "risk_compatibility": 0.10,     # 风控适配度
        "competition_level": 0.10,      # 竞争程度（反向）
    }
    
    def score(self, topic: Topic, account: Account) -> float:
        """
        综合评分 = Σ(维度分 × 权重)
        分数 > 7.0 才进入 writer 链路
        """
        scores = {
            "traffic_potential": self._calc_traffic(topic),
            "monetization_value": self._calc_monetization(topic, account),
            "evidence_availability": self._calc_evidence(topic),
            "human_scenario_fit": self._calc_human_fit(topic, account),
            "risk_compatibility": self._calc_risk(topic, account),
            "competition_level": self._calc_competition(topic),
        }
        
        total = sum(scores[k] * self.WEIGHTS[k] for k in scores)
        return total
```

#### 输出格式
```markdown
### 候选题 #1
- 问题：{title}
- URL：{url}
- 账号：L4 / L6
- 综合评分：8.2 / 10

#### 维度拆解
- 流量潜力：9/10（热榜第3，72万热度，230关注）
- 变现价值：8/10（AI工具带货场景，佣金预估15-30%）
- 证据可得性：7/10（可实测，有价格对比空间）
- 真人场景：9/10（程序员日常痛点，天然适合L4）
- 风控适配：8/10（非模板题，可写出个人判断）
- 竞争程度：7/10（88个回答，但高质量少）

#### 竞品样本（至少3个）
1. 样本A：开头用个人经历钩人，有截图证据...
2. 样本B：工具盘点型，AI味重，我们要避开...
3. 样本C：强判断型，推荐边界清晰...

#### 结论
- 建议：✅ 推荐今天进入 writer
- 最容易写出AI味的地方：{具体指出}
- 规避策略：{具体建议}
```

---

### 2.2 内容工厂 (Writer Agent)

#### 职责
- 根据 researcher 输出的候选题，生成内容草稿
- 严格遵循反AI检测写作规则
- 人工直写首段 + 关键取舍段，AI只做轻整理

#### 写作流水线
```
┌─────────────────────────────────────────────────────────┐
│                  Writer 写作流水线                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Step 1: 人工定观点                                      │
│  └─ "我到底想证明什么" → 一句话主判断                     │
│                                                         │
│  Step 2: 人工收证据                                      │
│  └─ 截图 / 价格 / 参数 / 实测 / 失败经验 (至少1个)       │
│                                                         │
│  Step 3: 人工写首段 + 关键取舍段                         │
│  └─ 这两段不能交给AI从0到1生成                           │
│                                                         │
│  Step 4: AI辅助整理                                      │
│  └─ 只做：顺序微调、删重复、修病句                       │
│  └─ 禁止：从空白直接生成最终公开稿                       │
│                                                         │
│  Step 5: 过风控闸门                                      │
│  └─ 10项硬闸门 + 账号专用闸门                            │
│                                                         │
│  Step 6: 人工确认发布                                    │
│  └─ 最终发布权在人工                                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### 内容模板库

##### L4 AI/程序员好物类
```markdown
## 模板：AI工具实测型

### 结构
1. 首段（人工直写）：直接给判断，这东西值不值得用，适合谁，不适合谁
2. 个人场景段：我为什么关心这个问题（职业/预算/设备/使用限制）
3. 实测证据段：截图/价格/参数/使用步骤/失败案例
4. 取舍段：谁适合、谁不适合、坑点、替代方案
5. 自然植入：只推荐1-2个，说明"不推荐"的边界
6. 结尾（不总结）：如果你是X就做Y，如果你是Z先别买

### 禁止
- "近年来/随着/在当今" 开头
- "背景→三点亮点→行业影响→总结" 结构
- 全程客观中立无判断
- 参数堆砌无场景
- 工具列表无选择理由
```

##### L6 故事/盐言类
```markdown
## 模板：悬疑故事型

### 结构
1. 开头100字内：人物 + 异常 + 冲突细节
2. 人物设定：有口癖、有利益、有隐瞒
3. 每800-1200字：一次信息翻转
4. 结尾：有余味，不解释全部

### 禁止
- "那是一个普通的夜晚" 等通用开头
- 全员工具人对白
- 结构整齐、对白工具化
- 工整AI短篇风格
```

#### 反AI检测检查清单
```python
class AntiAIChecker:
    """发布前反AI检测检查器"""
    
    BLACKLIST_PHRASES = [
        "近年来", "随着", "在当今", "不可否认", 
        "毫无疑问", "值得注意的是", "综上", "从长期来看"
    ]
    
    TEMPLATE_PATTERNS = [
        r"背景介绍.*三点亮点.*行业影响.*总结展望",
        r"首先.*其次.*再次.*最后",
        r"一方面.*另一方面.*总的来说",
    ]
    
    def check(self, content: str) -> CheckResult:
        """10项硬闸门检查"""
        checks = {
            "human_scenario": self._has_human_scenario(content),      # 具体人类场景
            "non_neutral_opinion": self._has_opinion(content),        # 非平均观点
            "real_tradeoff": self._has_tradeoff(content),             # 真实取舍
            "verifiable_detail": self._has_evidence(content),         # 可验证细节
            "natural_imperfection": self._has_natural_rhythm(content),# 自然瑕疵
            "no_ai_phrases": self._no_blacklist(content),             # 无AI套话
            "no_repeat_topic": self._no_repeat(content),              # 不连续同质
            "natural_product": self._natural_product(content),        # 商品自然出现
            "human_first_para": self._human_first_para(content),      # 首段人工直写
            "recovery_gate": self._recovery_gate(content),            # 恢复期闸门
        }
        
        passed = sum(1 for v in checks.values() if v)
        return CheckResult(passed=passed, total=10, details=checks)
```

---

### 2.3 风控闸门 (Safety Gate)

#### 职责
- 发布前最后一道防线
- 检查内容是否符合平台规则
- 防止AI识别、折叠、限流

#### 闸门层级
```
┌─────────────────────────────────────────────────────────┐
│                   三层风控闸门                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Layer 1: 通用闸门（所有账号）                           │
│  ├─ 内容是否明显适合这个账号？                           │
│  ├─ 是否有明确主判断？                                   │
│  ├─ 是否有具体场景或人物？                               │
│  ├─ 是否有可验证细节？                                   │
│  ├─ 是否有AI套话/模板结构？                              │
│  └─ 发布目标是否清晰？                                   │
│                                                         │
│  Layer 2: 账号专用闸门                                   │
│  ├─ L4: 首段直接给判断？写清适合/不适合？               │
│  ├─ L4: 有真实取舍/坑点？商品自然出现？                  │
│  ├─ L6: 开头100字有人物+异常+冲突？                      │
│  └─ L6: 人物像真人？有反转？                             │
│                                                         │
│  Layer 3: 恢复期补充闸门（如适用）                       │
│  ├─ 宁可少发不可错发                                     │
│  ├─ 不沿用被折叠内容的同款结构                           │
│  ├─ 首段/结论段/取舍段不交给AI                           │
│  ├─ 同热点48h内最多1篇                                   │
│  └─ 遮住账号名不像同一生产线                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### 风控状态机
```python
class AccountRiskState(Enum):
    NORMAL = "normal"           # 正常运营
    WARNING = "warning"         # 收到警告
    RECOVERY = "recovery"       # 恢复期
    SUSPENDED = "suspended"     # 暂停发布

class RiskStateMachine:
    """账号风控状态机"""
    
    def transition(self, account: Account, event: Event) -> AccountRiskState:
        """
        状态转移规则：
        - NORMAL + 收到AI警告 → WARNING
        - WARNING + 内容被折叠 → RECOVERY
        - RECOVERY + folded_count停止增加 + 新内容阅读恢复 → NORMAL
        - RECOVERY + 继续折叠 → SUSPENDED
        """
        pass
```

---

### 2.4 发布调度 (Publisher Agent)

#### 职责
- 管理多账号发布队列
- 控制发布节奏和频率
- 浏览器Profile隔离
- 发布后冷启动互动

#### 发布策略
```python
class PublishingScheduler:
    """发布调度器"""
    
    # 最佳发布时段（基于历史数据）
    OPTIMAL_WINDOWS = {
        "morning": ("10:00", "12:00"),    # 早高峰
        "noon": ("12:00", "13:30"),       # 午休
        "evening": ("19:00", "21:00"),    # 晚高峰
    }
    
    # 账号发布配额
    QUOTAS = {
        "L4": {"answers": 2, "ideas": 1, "articles": 1},
        "L6": {"answers": 2, "ideas": 1, "articles": 1},
    }
    
    # 防关联规则
    ANTI_CORRELATION = {
        "same_topic_gap_hours": 48,       # 同话题间隔
        "cross_account_gap_minutes": 30,  # 跨账号间隔
        "no_cross_like": True,            # 禁止互赞
        "no_cross_comment": True,         # 禁止互评
    }
    
    def schedule(self, contents: List[Content]) -> Schedule:
        """
        生成发布计划：
        1. 按账号分流（L4→AI/好物，L6→故事/盐言）
        2. 按时段分配（早/中/晚）
        3. 检查防关联规则
        4. 输出带时间戳的发布队列
        """
        pass
```

#### 浏览器自动化
```python
class CloakBrowser:
    """浏览器Profile隔离 + 自动化发布"""
    
    def __init__(self, account_key: str):
        self.profile_path = f"/Users/daxian/.openclaw/browser/{account_key}"
        self.cdp_port = self._get_cdp_port(account_key)
        
    async def publish_answer(self, question_url: str, content: str):
        """
        发布回答流程：
        1. 启动隔离浏览器Profile
        2. 导航到问题页
        3. 填入内容（模拟人工输入节奏）
        4. 检查AI标注提示
        5. 确认发布
        6. 记录发布结果
        """
        pass
    
    async def post_cold_start_interaction(self, answer_url: str):
        """
        发布后45分钟冷启动：
        - 自然浏览行为
        - 相关话题浏览
        - 不触发互赞/互评
        """
        pass
```

---

### 2.5 互动引擎 (Operator Agent)

#### 职责
- 监控评论区，及时回复
- 追踪内容数据（阅读/赞同/收藏/分享）
- 识别高潜力内容，建议自荐
- 日报汇总

#### 互动策略
```python
class InteractionEngine:
    """互动引擎"""
    
    # 评论回复规则
    COMMENT_RULES = {
        "min_length": 10,              # 最少10字
        "response_time": "2h",         # 2小时内回复
        "tone": "natural",             # 自然口吻
        "no_template": True,           # 禁止模板回复
    }
    
    # 数据追踪指标
    METRICS = [
        "reads", "upvotes", "comments", 
        "collections", "shares", "followers"
    ]
    
    async def monitor_and_respond(self, answer_url: str):
        """
        监控并回复评论：
        1. 抓取新评论
        2. 分类：提问/质疑/赞同/无关
        3. 生成自然回复（非模板）
        4. 人工确认后发布
        """
        pass
    
    def generate_daily_report(self, account: Account) -> DailyReport:
        """
        生成日报：
        - 今日发布内容
        - 数据变化（阅读/赞同/收藏）
        - AI风险观察（折叠/警告）
        - 收益追踪（佣金/活动奖励）
        - 明日建议
        """
        pass
```

---

### 2.6 收益引擎 (Revenue Agent)

#### 职责
- 追踪各变现渠道收益
- 识别高转化内容特征
- 优化好物推荐策略
- 活动/任务管理

#### 变现渠道
```python
class RevenueTracker:
    """收益追踪器"""
    
    CHANNELS = {
        "goods_recommendation": {
            "name": "好物推荐",
            "commission_rate": "10-30%",
            "best_categories": ["AI编程工具", "云服务器", "机械键盘", "编程书籍"],
            "tracking": "点击→出单→佣金",
        },
        "content_self_recommendation": {
            "name": "内容自荐",
            "quota": "3次/月",
            "best_for": "高阅读高赞同内容",
        },
        "brand_tasks": {
            "name": "芝士平台品牌任务",
            "requirement": "Lv4 + 创作分1000",
            "payment": "按任务结算",
        },
        "salt_story": {
            "name": "盐言故事",
            "monetization": "投稿/签约/分发收益",
            "best_for": "L6故事号",
        },
        "activity_rewards": {
            "name": "活动奖励",
            "types": ["创作打卡", "孵化计划", "话题活动"],
            "reward": "盐粒/现金/流量",
        },
    }
    
    def optimize_product_placement(self, content: Content) -> PlacementAdvice:
        """
        优化好物植入：
        1. 分析问题类型（工具选择/购买决策/使用体验）
        2. 匹配高佣金商品
        3. 建议植入位置（自然出现，非广告块）
        4. 预估转化率
        """
        pass
```

---

## 三、技术实现方案

### 3.1 技术栈
```yaml
核心框架:
  language: Python 3.11+
  async: asyncio + aiohttp
  browser: Playwright (隔离Profile)
  
数据存储:
  local_db: SQLite (发布历史/收益追踪)
  cache: Redis (热榜缓存/会话管理)
  config: YAML (账号配置/策略配置)
  
AI集成:
  llm: OpenAI API / Claude API / 本地模型
  embedding: text-embedding-3-small (语义搜索)
  prompt: Jinja2模板 (动态prompt)
  
调度:
  scheduler: APScheduler (定时任务)
  queue: Celery + Redis (异步任务队列)
  
监控:
  logging: structlog (结构化日志)
  metrics: Prometheus (可选)
  alerts: 微信/邮件通知
```

### 3.2 目录结构
```
zhihu-agent/
├── config/
│   ├── accounts.yaml          # 账号配置
│   ├── strategy.yaml          # 策略配置
│   └── secrets.yaml           # 密钥（gitignore）
│
├── agents/
│   ├── researcher.py          # 选题引擎
│   ├── writer.py              # 内容工厂
│   ├── safety_gate.py         # 风控闸门
│   ├── publisher.py           # 发布调度
│   ├── operator.py            # 互动引擎
│   └── revenue.py             # 收益引擎
│
├── browser/
│   ├── cloak_browser.py       # 浏览器隔离
│   ├── zhihu_pages.py         # 知乎页面操作
│   └── anti_detect.py         # 反检测策略
│
├── data/
│   ├── models.py              # 数据模型
│   ├── db.py                  # 数据库操作
│   └── cache.py               # 缓存管理
│
├── prompts/
│   ├── researcher.j2          # 选题prompt模板
│   ├── writer.j2              # 写作prompt模板
│   └── operator.j2            # 运营prompt模板
│
├── rules/
│   ├── anti_ai_detection.md   # 反AI检测规则
│   ├── pre_publish_gate.md    # 发布前闸门
│   └── recovery_sop.md        # 恢复期SOP
│
├── reports/
│   ├── daily/                 # 日报
│   ├── weekly/                # 周报
│   └── revenue/               # 收益报告
│
├── scripts/
│   ├── run_researcher.py      # 运行选题
│   ├── run_writer.py          # 运行写作
│   └── run_operator.py        # 运行运营
│
├── tests/
│   └── ...
│
├── main.py                    # 入口
└── README.md
```

### 3.3 核心数据模型
```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List

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

@dataclass
class Account:
    key: str                              # zhihu-l4 / zhihu-l6
    name: str                             # 不要开学秦小鱼 / 沐晨
    level: AccountLevel
    role: AccountRole
    browser_profile: str                  # /Users/daxian/.openclaw/browser/zhihu-l4
    cdp_port: int                         # 18804 / 18806
    risk_state: RiskState = RiskState.NORMAL
    creation_score: int = 0
    folded_count: int = 0
    
    # 变现权益
    goods_recommendation_enabled: bool = False
    content_recommendation_quota: int = 0
    brand_tasks_enabled: bool = False
    
@dataclass
class Topic:
    url: str
    title: str
    heat: int                             # 热度
    answers_count: int
    followers: int
    views: int
    domain: str                           # AI/科技/故事...
    
    # 评分
    score: float = 0.0
    monetization_value: float = 0.0
    evidence_availability: float = 0.0
    
    # 竞品样本
    competitor_samples: List[dict] = field(default_factory=list)

@dataclass
class Content:
    id: str
    account_key: str
    topic: Topic
    content_type: str                     # answer / article / idea
    title: str
    body: str
    word_count: int
    
    # 反AI检测
    ai_label: bool = False                # 是否标注AI辅助
    anti_ai_score: float = 0.0            # 反AI检测得分
    
    # 发布状态
    status: str = "draft"                 # draft / pending / published / folded
    published_at: Optional[datetime] = None
    published_url: Optional[str] = None
    
    # 数据追踪
    reads: int = 0
    upvotes: int = 0
    comments: int = 0
    collections: int = 0
    shares: int = 0
    
    # 变现
    products_planted: List[str] = field(default_factory=list)
    estimated_commission: float = 0.0

@dataclass
class DailyReport:
    date: str
    account_key: str
    
    # 发布
    contents_published: List[Content] = field(default_factory=list)
    contents_pending: List[Content] = field(default_factory=list)
    
    # 数据
    total_reads: int = 0
    total_upvotes: int = 0
    total_comments: int = 0
    
    # 风控
    folded_count: int = 0
    ai_warnings: int = 0
    risk_state: RiskState = RiskState.NORMAL
    
    # 收益
    commission_earned: float = 0.0
    activity_rewards: float = 0.0
    
    # 建议
    next_day_plan: List[str] = field(default_factory=list)
```

---

## 四、变现路径优化

### 4.1 L4 AI/程序员好物变现

```
┌─────────────────────────────────────────────────────────┐
│              L4 变现漏斗                                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  流量入口                                                │
│  ├─ 热榜AI话题（DeepSeek/GPT/Cursor等）                 │
│  ├─ 长尾SEO问题（程序员工具选择/硬件对比）               │
│  └─ 活动流量（科技创作者孵化计划等）                     │
│                                                         │
│  内容转化                                                │
│  ├─ 实测体验型（有截图/价格/参数）                       │
│  ├─ 强判断型（推荐/不推荐边界清晰）                      │
│  └─ 场景决策型（谁适合/谁不适合）                        │
│                                                         │
│  好物植入                                                │
│  ├─ 自然出现（先讲痛点，再出工具）                       │
│  ├─ 单一推荐（1-2个，不堆砌）                            │
│  └─ 高佣金品类（AI工具/云服务器/机械键盘）               │
│                                                         │
│  收益来源                                                │
│  ├─ 好物推荐佣金（10-30%）                               │
│  ├─ 芝士平台品牌任务（按任务结算）                       │
│  ├─ 内容自荐（流量加持→间接变现）                        │
│  └─ 活动奖励（盐粒/现金）                                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### 高转化内容特征
```python
HIGH_CONVERSION_PATTERNS = {
    "question_types": [
        "XX工具值不值得买/用？",
        "XX和YY怎么选？",
        "程序员必备工具有哪些？",
        "如何评价XX的价格/性能？",
    ],
    "content_features": [
        "有实测截图",
        "有价格对比表",
        "有使用场景描述",
        "有明确推荐边界",
        "有失败经验/坑点",
    ],
    "product_categories": [
        ("Cursor", "AI编程工具", "15-30%"),
        ("通义灵码", "AI编程工具", "10-20%"),
        ("云服务器", "基础设施", "10-25%"),
        ("机械键盘", "外设", "8-15%"),
        ("编程书籍", "知识付费", "20-40%"),
    ],
}
```

### 4.2 L6 故事/盐言变现

```
┌─────────────────────────────────────────────────────────┐
│              L6 变现漏斗                                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  流量入口                                                │
│  ├─ 悬疑/灵异/细思极恐话题                              │
│  ├─ 盐言故事热点投稿                                     │
│  └─ 历史高阅读内容盘活                                   │
│                                                         │
│  内容转化                                                │
│  ├─ 强冲突开头（100字内人物+异常+冲突）                  │
│  ├─ 人物立体（有口癖/利益/隐瞒）                         │
│  └─ 信息翻转（每800-1200字一次）                         │
│                                                         │
│  变现路径                                                │
│  ├─ 盐言投稿/签约（按阅读/分成）                         │
│  ├─ 内容自荐（高阅读故事→自荐→更多流量）                 │
│  ├─ 故事热点投稿（蹭热点→流量→收益）                     │
│  └─ 历史内容盘活（旧故事更新→重新分发）                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 五、风控体系

### 5.1 风控层级
```
┌─────────────────────────────────────────────────────────┐
│                  风控金字塔                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Level 4: 平台规则合规                                   │
│  ├─ 知乎社区规范                                         │
│  ├─ AI内容披露要求                                       │
│  └─ 广告法/消保法                                        │
│                                                         │
│  Level 3: 反AI检测                                       │
│  ├─ 避免模板化结构                                       │
│  ├─ 避免AI套话                                           │
│  ├─ 增加真人痕迹（瑕疵/口语/个人判断）                   │
│  └─ 控制发布频率和同质度                                 │
│                                                         │
│  Level 2: 账号安全                                       │
│  ├─ 浏览器Profile隔离                                    │
│  ├─ 防关联（不互赞/不互评/不同IP）                       │
│  ├─ 登录态管理                                           │
│  └─ 异常行为检测                                         │
│                                                         │
│  Level 1: 内容质量                                       │
│  ├─ 有证据/有场景/有判断                                 │
│  ├─ 非百科式复制粘贴                                     │
│  ├─ 非低质灌水                                           │
│  └─ 符合账号定位                                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 5.2 恢复期策略
```python
class RecoveryStrategy:
    """恢复期执行策略"""
    
    PHASES = {
        "A_止血期": {
            "duration": "3-7天",
            "goal": "不再继续向平台喂同类高风险样本",
            "actions": [
                "暂停高风险模板文发布",
                "暂停同一天连续发2-3篇同质内容",
                "暂停热点解释+三点分析+温和结尾写法",
                "允许：修订旧文（补截图/补失败经验）",
                "允许：少量新发（强场景+强判断+强证据）",
            ],
            "exit_criteria": [
                "folded_count不继续快速增加",
                "新发内容不再立刻出现同类折叠",
            ],
        },
        "B_恢复期": {
            "duration": "第2周",
            "goal": "重建真人作者信号",
            "actions": [
                "每篇只解决一个问题",
                "每篇写清：支持什么/反对什么/适合谁/不适合谁",
                "每篇至少1个可验证证据",
                "首段必须人工直写",
                "发布后10-60分钟可自然补充编辑",
            ],
            "exit_criteria": [
                "新内容24h阅读明显高于折叠内容基线",
                "评论区出现真实追问/反驳",
                "不再出现连续全军折叠",
            ],
        },
        "C_重启变现期": {
            "duration": "第3周后",
            "goal": "在账号信号恢复后逐步恢复自然变现",
            "actions": [
                "每篇只保留1个主推荐",
                "先讲使用场景和决策逻辑，再自然出现工具",
                "优先高客单/高相关/低植入密度",
                "允许部分内容不带货（维持分发和信任）",
            ],
            "exit_criteria": [
                "内容不再折叠",
                "阅读和互动恢复正常基线",
                "点击/收藏/出单/佣金恢复",
            ],
        },
    }
```

---

## 六、自动化流水线

### 6.1 日常执行流程
```
┌─────────────────────────────────────────────────────────┐
│              日常执行时间线                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  10:00 - Researcher 选题                                 │
│  ├─ 扫描热榜/长尾问题                                    │
│  ├─ 评估候选题（评分+竞品样本）                          │
│  └─ 输出：2-4个候选题 + 建议                            │
│                                                         │
│  11:00 - Writer 写作（早场）                             │
│  ├─ 读取researcher输出                                   │
│  ├─ 人工定观点+收证据+写首段                             │
│  ├─ AI辅助整理                                           │
│  └─ 输出：1-2篇内容草稿                                 │
│                                                         │
│  11:30 - 风控闸门检查                                    │
│  ├─ 10项硬闸门                                           │
│  ├─ 账号专用闸门                                         │
│  └─ 输出：通过/不通过 + 修改建议                        │
│                                                         │
│  12:00 - Publisher 发布（午场）                          │
│  ├─ 人工确认最终稿                                       │
│  ├─ 浏览器自动化发布                                     │
│  └─ 记录发布结果                                         │
│                                                         │
│  12:45 - 冷启动互动                                      │
│  ├─ 自然浏览行为                                         │
│  └─ 相关话题浏览                                         │
│                                                         │
│  14:00 - Operator 监控                                   │
│  ├─ 检查评论区                                           │
│  ├─ 回复评论（人工确认后）                               │
│  └─ 追踪数据变化                                         │
│                                                         │
│  19:00 - Writer 写作（晚场）                             │
│  ├─ 可选：更新旧文 / 新写第2篇                           │
│  └─ 同样过风控闸门                                       │
│                                                         │
│  20:00 - Publisher 发布（晚场）                          │
│  └─ 同午场流程                                           │
│                                                         │
│  21:00 - Operator 日报                                   │
│  ├─ 汇总今日发布/数据/风控/收益                          │
│  └─ 输出明日建议                                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 6.2 定时任务配置
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# 10:00 选题
@scheduler.scheduled_job("cron", hour=10, minute=0)
async def run_researcher():
    researcher = ResearcherAgent()
    topics = await researcher.scan_and_score()
    await researcher.save_recommendations(topics)

# 11:00 写作（早场）
@scheduler.scheduled_job("cron", hour=11, minute=0)
async def run_writer_morning():
    writer = WriterAgent()
    drafts = await writer.generate_drafts(session="morning")
    await writer.save_drafts(drafts)

# 11:30 风控检查
@scheduler.scheduled_job("cron", hour=11, minute=30)
async def run_safety_gate():
    gate = SafetyGate()
    results = await gate.check_all_pending()
    await gate.save_results(results)

# 12:00 发布（午场）
@scheduler.scheduled_job("cron", hour=12, minute=0)
async def run_publisher_noon():
    publisher = PublisherAgent()
    await publisher.publish_approved(session="noon")

# 14:00 监控互动
@scheduler.scheduled_job("cron", hour=14, minute=0)
async def run_operator():
    operator = OperatorAgent()
    await operator.monitor_and_respond()
    await operator.track_metrics()

# 19:00 写作（晚场）
@scheduler.scheduled_job("cron", hour=19, minute=0)
async def run_writer_evening():
    writer = WriterAgent()
    drafts = await writer.generate_drafts(session="evening")
    await writer.save_drafts(drafts)

# 20:00 发布（晚场）
@scheduler.scheduled_job("cron", hour=20, minute=0)
async def run_publisher_evening():
    publisher = PublisherAgent()
    await publisher.publish_approved(session="evening")

# 21:00 日报
@scheduler.scheduled_job("cron", hour=21, minute=0)
async def run_daily_report():
    operator = OperatorAgent()
    report = await operator.generate_daily_report()
    await operator.save_report(report)
```

---

## 七、关键成功因素

### 7.1 内容质量 > 数量
```
❌ 错误做法：
- 每天发5-10篇模板化内容
- 追求数量忽视质量
- 批量生产同质内容

✅ 正确做法：
- 每天2-3篇高质量内容
- 每篇有证据/场景/判断
- 宁可少发也不发低质内容
```

### 7.2 真人痕迹 > AI完美
```
❌ AI特征：
- 结构工整（首先/其次/再次/最后）
- 语气中立（有利有弊/还需观察）
- 无个人判断（客观陈述）
- 无具体细节（泛泛而谈）

✅ 真人特征：
- 结构自然（允许不工整）
- 有明确立场（我支持/我反对）
- 有个人经历（我遇到过/我测过）
- 有具体细节（截图/价格/参数）
```

### 7.3 长期主义 > 短期爆发
```
❌ 短期思维：
- 为了变现牺牲内容质量
- 为了流量做标题党
- 为了效率用模板批量生产

✅ 长期思维：
- 建立账号信任和权重
- 积累高质量内容资产
- 可持续的变现模式
```

---

## 八、实施路线图

### Phase 1: 基础框架（1-2周）
- [ ] 搭建项目结构
- [ ] 实现数据模型
- [ ] 实现浏览器隔离（CloakBrowser）
- [ ] 实现基础发布功能

### Phase 2: 核心Agent（2-3周）
- [ ] 实现Researcher（选题引擎）
- [ ] 实现Writer（内容工厂）
- [ ] 实现SafetyGate（风控闸门）
- [ ] 实现Publisher（发布调度）

### Phase 3: 运营闭环（1-2周）
- [ ] 实现Operator（互动引擎）
- [ ] 实现Revenue（收益追踪）
- [ ] 实现日报/周报生成
- [ ] 接入通知（微信/邮件）

### Phase 4: 优化迭代（持续）
- [ ] 根据数据优化选题评分模型
- [ ] 根据折叠情况优化反AI策略
- [ ] 根据转化数据优化好物植入
- [ ] 扩展更多变现渠道

---

## 九、风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| AI识别折叠 | 账号权重下降，流量减少 | 严格执行反AI检测规则，恢复期SOP |
| 账号关联 | 多账号被封 | 浏览器Profile隔离，防关联策略 |
| 平台规则变化 | 现有策略失效 | 持续监控规则变化，快速调整 |
| 收益不达预期 | 投入产出比低 | 小步快跑，快速验证，及时止损 |
| 内容质量下降 | 用户流失，权重下降 | 质量>数量，宁缺毋滥 |

---

## 十、总结

知乎Agent系统的核心不是"自动化批量发布"，而是：

1. **选题精准**：找到流量+变现+风控的最佳平衡点
2. **内容优质**：每篇都有证据/场景/判断，像真人创作
3. **风控严格**：多层闸门，宁可少发也不发高风险内容
4. **变现自然**：好物植入自然出现，不硬塞广告
5. **持续迭代**：根据数据反馈不断优化策略

最终目标：**建立可持续的知乎内容变现系统，而不是短期薅羊毛。**
