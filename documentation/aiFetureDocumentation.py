LactureQuestionAnswerGenerationModel = """
**Course Video Question Generation**

**Definition**
Whenever this document mentions a "question" it means:
- 1 question stem
- 4 answer options
- 1 correct answer (indicated)
- 1 short explanation/solution for the correct answer

**Overview**
This API automatically generates assessment questions for course videos. It supports both initial question creation for a new course and incremental generation when videos are added to an existing course. The endpoint identifies which videos need questions and creates a consistent, difficulty-balanced set of questions for each target video.

**Supported Use Cases**
1. **New course with no existing questions**  
   If a course has no questions at all, the API will generate questions for *every* video in the course.

2. **Existing course that already has some questions + newly added videos**  
   If a course already contains videos with previously generated questions but you have added one or more new videos, the API will generate questions only for the videos that required questions to be generated [it culd be for the videos that already has question + newly added videos].  
   - It does not matter how many new videos were added or where they were inserted (beginning, middle, or end).  

**Input Parameters (API payload)**
- `course_id` (string, required)  
  The unique identifier of the course for which questions should be generated.

- `questions_per_video` (integer, required)  
  The number of questions to generate for each targeted video.  
  - For a balanced difficulty mix, choose a value divisible by 3. When divisible by 3, the API will produce an equal number of Easy / Medium / Hard questions per video.  
  - It should be at least 3 and smaller then 21.

- `is_hinglish` (boolean, optional, default: false)  
  Set to `true` if the video language is a Hindi-English mix ("Hinglish"); otherwise `false`. This helps the model select phrasing and vocabulary appropriate for the video language.
"""