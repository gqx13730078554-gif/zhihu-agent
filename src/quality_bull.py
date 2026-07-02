"""Quality Bull Writer - 主张内容可以发布"""

class QualityBull:
    """质量辩论中的看多方 - 主张内容优点"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    def argue(self, content: str, debate_history: str = "") -> str:
        """为内容质量辩护，列举优点"""
        prompt = f"""你是一个内容质量评审员，负责为一篇知乎回答的质量辩护。

你的任务：
1. 找出这篇回答的优点（真实感、专业性、实用性等）
2. 说明为什么这篇回答可以直接发布
3. 如果有bear提出的问题，你需要回应并说明为什么不需要修改

辩论历史：
{debate_history if debate_history else "（首轮辩论）"}

回答内容：
{content}

请用简洁的语言（150字以内）阐述你的观点，重点说明：
- 这篇回答的3个主要优点
- 为什么这些优点足以让它直接发布
- 如果有bear的问题，简要回应

格式：
【Quality Bull观点】
优点1：...
优点2：...
优点3：...
结论：..."""
        
        response = self.llm_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        return response.choices[0].message.content
