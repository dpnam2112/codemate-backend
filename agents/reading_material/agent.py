from typing import List, Optional
from openai import AsyncOpenAI
from core.settings import settings as env_settings
from pydantic import BaseModel

class AIGenReadingMaterialSchema(BaseModel):
    reading_material: str
    questions: List[str]

class ReadingMaterialAgent:
    def __init__(self):
        self.openai_client = AsyncOpenAI(
                api_key=env_settings.OPENAI_API_KEY
            )

    async def generate_reading_material(
        self, module_description: str, student_profile: Optional[str] = None
    ) -> AIGenReadingMaterialSchema:
        """
        Generate tailored reading material based on the student's profile, module description, and learning outcomes.
        """

        prompt = f"""
You are an intelligent educational content generation assistant as well as an expert in educational psychology. Your task is to create tailored reading material for a student based on their course-specific profile and the given module description. Your primary goal is to create reading material that is easy to understand, engaging, and informative while promoting deeper learning and critical thinking.

The reading material should:
- Be presented in a **clear and concise** manner, using simple language and **avoiding technical jargon** where possible.
- Break down complex concepts into **smaller, digestible parts** with **step-by-step explanations**.
- Use **real-life examples**, **analogies**, and **visual descriptions** to make abstract concepts more relatable.
- Incorporate **visual aids or diagrams** where applicable, and use **bulleted lists** to enhance readability.
- Include **recap sections** and **key takeaways** at the end of each topic to reinforce learning.
- Offer **self-assessment prompts** to encourage reflection and understanding.

Additionally:
- Make sure the reading material is engaging and relevant to the student's current learning stage and goals.
- Align the content with the **intended learning outcomes** and address both the student's strengths and areas needing improvement.
- Structure the material with **clear headings and subheadings** for easy navigation.

Next, generate a structured list of questions that align with **Bloom's Taxonomy**, ensuring that questions progressively increase in complexity:
- **Remembering**: Questions that test recall of key facts and concepts.
- **Understanding**: Questions that require the student to explain concepts in their own words.
- **Applying**: Questions that ask the student to use the concepts in practical scenarios.
- **Analyzing**: Questions that encourage breaking down ideas and making connections.
- **Evaluating**: Critical thinking questions that require judgments based on evidence.
- **Creating**: Open-ended questions that prompt the student to generate new ideas or solutions.
        """

        module_description_prompt = f"""
        Module description:
        {module_description}
        """

        response = await self.openai_client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": module_description_prompt}
            ],
            response_format=AIGenReadingMaterialSchema
        )

        structured_resp = response.choices[0].message.parsed
        if structured_resp is None: 
            raise ValueError(
                "Error while generating reading material: structured response is expected"
            )
        return structured_resp
