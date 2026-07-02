"""Quality Bear Writer - 指出内容问题并提出修改建议"""

class QualityBear:
    """质量辩论中的看空方 - 指出内容问题"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    def argue(self, content: str, debate_history: str = "") -> str:
        """指出内容问题，提出修改建议"""
        prompt = f"""你是一个内容质量评审员，负责严格审查一篇知乎回答的质量问题。

你的任务：
1. 找出这篇回答的问题（AI痕迹、逻辑漏洞、表达不当等）
2. 提出具体的修改建议
3. 如果有bull的辩护，你需要反驳并说明为什么仍需修改

辩论历史：
{debate_history if debate_history else "（首轮辩论）"}

回答内容：
{content}

请用简洁的语言（150字以内）阐述你的观点，重点说明：
- 这篇回答的3个主要问题
- 具体的修改建议
- 如果不修改可能带来的风险

格式：
【Quality Bear观点】
问题1：...
问题2：...
问题3：...
修改建议：...
风险：..."""
        
        response = self.llm_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        return response.choices[0].message.content
