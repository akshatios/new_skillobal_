import io
import json
import uuid
import shutil
import zipfile
import asyncio
from typing import List
from pathlib import Path
from datetime import datetime
from langchain_xai import ChatXAI
from core.config import ai_api_secrets
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableParallel
from langchain_google_genai import ChatGoogleGenerativeAI
from helper_function.apis_requests import get_current_user
from fastapi import Request, UploadFile, File, Form, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.runnables.passthrough import RunnableAssign
from helper_function.ai_feature_helper_function.runnable_lambda import extract_summary, extract_questions
from core.database import courses_collection, courses_videos_collection, course_question_and_answers_collection

from helper_function.ai_feature_helper_function.prompt_templates import (
    summary_prompt, 
    question_prompt_multi_model,
    cumulative_summary_prompt,
    question_selection_prompt
)
from helper_function.ai_feature_helper_function.schema_definitions import (
    summary_json_schema, 
    question_json_schema,
    cumulative_summary_json_schema
)
from helper_function.ai_feature_helper_function.video_to_pdf_function import (
    split_pdf, 
    write_file, 
    audio_to_text,
    video_to_audio, 
    save_text_to_pdf,
    sanitize_question_dict
)
from helper_function.ai_feature_helper_function.mongodb_helper import (
    fetch_course_videos,
    download_video_from_url,
    save_results_to_mongodb,
    chunk_videos
)

def init_models():
    """Initialize all AI models for parallel processing"""
    try:
        # Summary generation model (single model)
        summary_model = ChatOpenAI(model="gpt-5.1-2025-11-13")
        
        # Cumulative summary generation model (single model)
        cumulative_summary_model = ChatOpenAI(model="gpt-5.1-2025-11-13")
        
        # Multiple models for question generation (parallel processing)
        question_models = {
            "openai": ChatOpenAI(model="gpt-5.1-2025-11-13"),
            "anthropic": ChatOpenAI(model="gpt-5.1-2025-11-13"),
            "xai": ChatXAI(model="grok-4-fast-reasoning"),
            "google": ChatGoogleGenerativeAI(model="gemini-2.5-flash")
        }
        # question_models = {
        #     "openai": ChatOpenAI(model="gpt-5.1-2025-11-13"),
        #     "anthropic": ChatOpenAI(model="gpt-5.1-2025-11-13"),
        #     "xai": ChatOpenAI(model="gpt-5.1-2025-11-13"),
        #     "google": ChatOpenAI(model="gpt-5.1-2025-11-13")
        # }
        
        # Question selection model (best question picker)
        selection_model = ChatOpenAI(model="gpt-5.1-2025-11-13")

        # Structured outputs
        structured_summary_model = summary_model.with_structured_output(summary_json_schema)
        structured_cumulative_summary_model = cumulative_summary_model.with_structured_output(
            cumulative_summary_json_schema
        )
        structured_question_models = {
            name: model.with_structured_output(question_json_schema) 
            for name, model in question_models.items()
        }
        structured_selection_model = selection_model.with_structured_output(question_json_schema)
        
        return (
            structured_summary_model,
            structured_cumulative_summary_model,
            structured_question_models,
            structured_selection_model
        )
    except Exception as err:
        raise Exception(f"Model initialization failed: {err}")

async def paths():
    """Create all necessary directory paths"""
    try:
        base_dir = ai_api_secrets.BASE_DIR 
        request_id = str(uuid.uuid4())
        data_dir = base_dir / "data" / request_id
        output_dir = data_dir / "output"
        
        all_paths = {
            "base_dir": base_dir,
            "data_dir": data_dir,
            "output_dir": output_dir,
            "input_video_dir": data_dir / "input_video",
            "input_audio_dir": data_dir / "input_audio",
            "input_text_dir": data_dir / "input_text",
            "input_pdf_dir": data_dir / "input_pdf",
            "split_pdf_dir": data_dir / "split_pdf",
            "lecture_summaries_dir": output_dir / "lecture_summaries",
            "lecture_questions_dir": output_dir / "lecture_questions",
            "cumulative_questions_dir": output_dir / "cumulative_questions",
            "all_previous_lecture_summary_file": output_dir / "all_previous_lecture_summary.txt",
            "font_path": base_dir / "helper_function" / "ai_feature_helper_function" /"font" / "Poppins-Regular.ttf"
        }
        
        # Create all directories
        for key, path in all_paths.items():
            if key.endswith("_dir"):
                await asyncio.to_thread(path.mkdir, exist_ok=True, parents=True)
        
        return all_paths
    except Exception as err:
        raise Exception(f"Path creation failed: {err}")

async def pdf_loader(pdf_path: Path) -> str:
    """Load PDF and extract text"""
    try:
        loader = PyPDFLoader(str(pdf_path))
        docs = await loader.aload()
        return docs[0].page_content
    except Exception as err:
        raise Exception(f"PDF loading failed: {err}")

def create_summary_chain(structured_summary_model):
    """Create chain for page summary generation"""
    try:
        summary_chain = summary_prompt | structured_summary_model
        chain = RunnableAssign(RunnableParallel({"summary_output": summary_chain}))
        final_chain = chain | extract_summary
        return final_chain
    except Exception as err:
        raise Exception(f"Summary chain creation failed: {err}")

def create_question_generation_chain(structured_question_models):
    """Create parallel chain for question generation using multiple models"""
    try:
        # Create parallel chains for each model
        parallel_chains = {
            f"{name}_questions": question_prompt_multi_model | model
            for name, model in structured_question_models.items()
        }
        question_chain = RunnableAssign(RunnableParallel(parallel_chains))
        final_chain = question_chain | extract_questions
        return final_chain
    except Exception as err:
        raise Exception(f"Question generation chain creation failed: {err}")

def create_question_selection_chain(structured_selection_model):
    """Create chain for selecting best questions from multiple model outputs"""
    try:
        selection_chain = question_selection_prompt | structured_selection_model
        return selection_chain
    except Exception as err:
        raise Exception(f"Question selection chain creation failed: {err}")

def create_cumulative_summary_chain(structured_cumulative_summary_model):
    """Create chain for combining lecture summaries"""
    try:
        cumulative_chain = cumulative_summary_prompt | structured_cumulative_summary_model
        return cumulative_chain
    except Exception as err:
        raise Exception(f"Cumulative summary chain creation failed: {err}")

async def process_single_page(
    page_num: int,
    split_pdf_dir: Path,
    previous_pages_summary: str,
    summary_chain,
    number_of_questions: int
) -> tuple:
    """Process a single PDF page to generate summary"""
    try:
        current_page_number = page_num + 1
        pdf_name = split_pdf_dir / f"page_{current_page_number}.pdf"
        page_text = await pdf_loader(pdf_name)
        
        result = await summary_chain.ainvoke({
            "page_text": page_text,
            "cumulative_concise_summary": previous_pages_summary,
            "number_of_questions": number_of_questions,
            "number_of_questions_in_each_category": number_of_questions // 3
        })
        
        concise_summary = result["concise_page_summary"]
        detailed_summary = result["detail_page_summary"]
        
        # Format summaries with page numbers
        formatted_concise = f"\n\n#### Page {current_page_number}:\n{concise_summary}\n"
        formatted_detailed = f"\n\n#### Page {current_page_number}:\n{detailed_summary}\n"
        
        return formatted_concise, formatted_detailed
    except Exception as err:
        raise Exception(f"Page processing failed for page {page_num}: {err}")

async def generate_questions_for_lecture(
    lecture_summary: str,
    question_generation_chain,
    question_selection_chain,
    number_of_questions: int
) -> dict:
    """Generate questions using multiple models and select the best ones"""
    try:
        # Step 1: Generate questions from multiple models in parallel
        all_model_questions = await question_generation_chain.ainvoke({
            "lecture_summary": lecture_summary,
            "number_of_questions": number_of_questions,
            "number_of_questions_in_each_category": number_of_questions // 3
        })
        # Sanitize all model outputs
        all_model_questions_sanitized = sanitize_question_dict(all_model_questions)
        
        # Step 2: Use selection model to pick best questions
        best_questions = await question_selection_chain.ainvoke({
            "all_model_questions": all_model_questions_sanitized,
            "lecture_summary": lecture_summary,
            "number_of_questions": number_of_questions,
            "number_of_questions_in_each_category": number_of_questions // 3
        })
        
        # Sanitize final output (double-check)
        best_questions_sanitized = sanitize_question_dict(best_questions)
        
        return best_questions_sanitized
        
    except Exception as err:
        raise Exception(f"Question generation failed: {err}")

async def process_single_lecture(
    lecture_idx: int,
    lecture_pdf_path: Path,
    split_pdf_dir: Path,
    summary_chain,
    number_of_questions: int,
    lecture_summaries_dir: Path
) -> tuple:
    """Process a single lecture to generate page-wise summaries"""
    try:
        
        
        
        # Split PDF into pages
        total_pages = await split_pdf(lecture_pdf_path, split_pdf_dir)
        
        
        # Process each page sequentially
        cumulative_concise = ""
        cumulative_detailed = ""
        
        for page_num in range(total_pages):
            
            
            concise, detailed = await process_single_page(
                page_num=page_num,
                split_pdf_dir=split_pdf_dir,
                previous_pages_summary=cumulative_concise,
                summary_chain=summary_chain,
                number_of_questions=number_of_questions
            )
            
            cumulative_concise += concise
            cumulative_detailed += detailed
            
            # Save progress after each page
            await asyncio.gather(
                write_file(
                    lecture_summaries_dir / f"lecture_{lecture_idx + 1}_concise_summary.txt",
                    cumulative_concise
                ),
                write_file(
                    lecture_summaries_dir / f"lecture_{lecture_idx + 1}_detailed_summary.txt",
                    cumulative_detailed
                )
            )
        
        
        return cumulative_concise, cumulative_detailed
    except Exception as err:
        raise Exception(f"Lecture processing failed for lecture {lecture_idx}: {err}")

async def cleanup(all_paths):
    """Clean up temporary files"""
    try:
        if all_paths["data_dir"].exists():
            await asyncio.to_thread(shutil.rmtree, all_paths["data_dir"])
    except Exception as err:
        raise Exception(f"Cleanup failed: {err}")

async def QuestionAnswerGenerationModel(
    request: Request, token: str = Depends(get_current_user), 
    course_id: str = Form(...),  # CHANGED: Now takes course_id instead of uploaded files
    number_of_questions: int = Form(...),
    hinglish: bool = Form(...)
):
    """
    Main API endpoint for question generation from course videos stored in MongoDB.
    
    CHANGES:
    1. Takes course_id as input instead of uploaded files
    2. Fetches videos from MongoDB
    3. Downloads videos from URLs
    4. Processes videos in batches of 5
    5. Saves results to MongoDB collection
    """
    try:
        # Validation
        if number_of_questions < 3 or number_of_questions > 21:
            return JSONResponse(
                content={"message": "Number must be between 3 and 21"},
                status_code=400
            )
        if number_of_questions % 3 != 0:
            return JSONResponse(
                content={"message": "Number must be divisible by 3"},
                status_code=400
            )
        
        # NEW: Fetch videos from MongoDB
        # print(f"\n{'='*60}")
        # print(f"Fetching videos for course ID: {course_id}")
        # print(f"{'='*60}")
        
        videos = await fetch_course_videos(
            course_id=course_id,
            courses_collection=courses_collection,
            courses_videos_collection=courses_videos_collection
        )
        
        if not videos:
            return JSONResponse(
                content={"message": "No videos found for this course"},
                status_code=404
            )
        
        # print(f"Found {len(videos)} videos to process")
        
        # NEW: Split videos into batches of 5
        video_batches = chunk_videos(videos, batch_size=5)
        # print(f"Split into {len(video_batches)} batches (5 videos each)")
        
        # Initialize
        all_paths = await paths()
        (
            summary_model,
            cumulative_summary_model,
            question_models,
            selection_model
        ) = init_models()
        
        # Create chains
        summary_chain = create_summary_chain(summary_model)
        question_generation_chain = create_question_generation_chain(question_models)
        question_selection_chain = create_question_selection_chain(selection_model)
        cumulative_summary_chain = create_cumulative_summary_chain(cumulative_summary_model)
        
        # NEW: Storage for results (to save to MongoDB at the end)
        all_lecture_questions = {}
        all_cumulative_questions = {}
        all_lecture_summaries = {}
        all_previous_lecture_summary = ""
        total_lectures_processed = 0
        
        # NEW: Process each batch of videos
        for batch_idx, batch_videos in enumerate(video_batches):
            # print(f"\n{'='*60}")
            # print(f"Processing Batch {batch_idx + 1}/{len(video_batches)}")
            # print(f"Videos in this batch: {len(batch_videos)}")
            # print(f"{'='*60}")
            
            lecture_pdfs = []
            
            # Process videos in current batch to PDFs
            for video_idx, video in enumerate(batch_videos):
                global_video_idx = batch_idx * 5 + video_idx
                
                video_url = video.get("videoUrl")
                video_title = video.get("video_title", f"Video {global_video_idx + 1}")
                
                if not video_url:
                    # print(f"Skipping video {global_video_idx + 1}: No URL found")
                    continue
                
                # print(f"\nProcessing Video {global_video_idx + 1}: {video_title}")
                
                # NEW: Download video from URL
                video_target = all_paths["input_video_dir"] / f"input_{global_video_idx}.mp4"
                # print(f"  → Downloading video from URL...")
                await download_video_from_url(video_url, video_target)
                
                # Rest of the processing (same as before)
                audio_target = all_paths["input_audio_dir"] / f"input_{global_video_idx}.mp3"
                text_file_path = all_paths["input_text_dir"] / f"input_{global_video_idx}.txt"
                pdf_path = all_paths["input_pdf_dir"] / f"lecture_{global_video_idx + 1}.pdf"
                
                # print(f"  → Converting to audio...")
                await video_to_audio(video_target, output_path=audio_target)
                
                # print(f"  → Transcribing audio...")
                await audio_to_text(
                    path=audio_target,
                    text_file_path=text_file_path,
                    hinglish=hinglish
                )
                
                # print(f"  → Converting to PDF...")
                await save_text_to_pdf(
                    text_file_path=text_file_path,
                    output_path=pdf_path,
                    font_path=all_paths["font_path"]
                )
                
                lecture_pdfs.append({
                    "pdf_path": pdf_path,
                    "video_title": video_title,
                    "global_idx": global_video_idx
                })
                
                # print(f"✓ Video {global_video_idx + 1} processed successfully")
            
            # Process each lecture in the batch
            for lecture_info in lecture_pdfs:
                lecture_idx = lecture_info["global_idx"]
                lecture_pdf = lecture_info["pdf_path"]
                video_title = lecture_info["video_title"]
                
                # print(f"\n--- Generating Summary for Lecture {lecture_idx + 1}: {video_title} ---")
                
                # Create lecture-specific split directory
                lecture_split_dir = all_paths["split_pdf_dir"] / f"lecture_{lecture_idx + 1}"
                await asyncio.to_thread(lecture_split_dir.mkdir, parents=True, exist_ok=True)
                
                # Generate summaries
                lecture_concise, lecture_detailed = await process_single_lecture(
                    lecture_idx=lecture_idx,
                    lecture_pdf_path=lecture_pdf,
                    split_pdf_dir=lecture_split_dir,
                    summary_chain=summary_chain,
                    number_of_questions=number_of_questions,
                    lecture_summaries_dir=all_paths["lecture_summaries_dir"]
                )
                
                # NEW: Store summaries for MongoDB
                all_lecture_summaries[f"lecture_{lecture_idx + 1}"] = {
                    "video_title": video_title,
                    "concise_summary": lecture_concise,
                    "detailed_summary": lecture_detailed
                }
                
                # Generate lecture-specific questions
                # print(f"  → Generating questions for Lecture {lecture_idx + 1}...")
                lecture_questions = await generate_questions_for_lecture(
                    lecture_summary=lecture_detailed,
                    question_generation_chain=question_generation_chain,
                    question_selection_chain=question_selection_chain,
                    number_of_questions=number_of_questions
                )
                
                # NEW: Store questions for MongoDB
                all_lecture_questions[f"lecture_{lecture_idx + 1}"] = {
                    "video_title": video_title,
                    "questions": lecture_questions
                }
                
                await write_file(
                    all_paths["lecture_questions_dir"] / f"lecture_{lecture_idx + 1}_questions.json",
                    lecture_questions
                )
                
                # Update cumulative summary
                if total_lectures_processed == 0:
                    all_previous_lecture_summary = lecture_concise
                else:
                    # print(f"  → Updating cumulative summary...")
                    cumulative_result = await cumulative_summary_chain.ainvoke({
                        "previous_lectures_summary": all_previous_lecture_summary,
                        "new_lecture_summary": lecture_concise,
                        "lecture_number": total_lectures_processed + 1
                    })
                    all_previous_lecture_summary = cumulative_result["combined_summary"]
                
                await write_file(
                    all_paths["all_previous_lecture_summary_file"],
                    all_previous_lecture_summary
                )
                
                # Generate cumulative questions (from lecture 2 onwards)
                if total_lectures_processed > 0:
                    # print(f"  → Generating cumulative questions (Lectures 1-{total_lectures_processed + 1})...")
                    cumulative_questions = await generate_questions_for_lecture(
                        lecture_summary=all_previous_lecture_summary,
                        question_generation_chain=question_generation_chain,
                        question_selection_chain=question_selection_chain,
                        number_of_questions=number_of_questions
                    )
                    
                    # NEW: Store cumulative questions for MongoDB
                    all_cumulative_questions[f"lectures_1_to_{total_lectures_processed + 1}"] = {
                        "questions": cumulative_questions
                    }
                    
                    await write_file(
                        all_paths["cumulative_questions_dir"] / f"cumulative_lectures_1_to_{total_lectures_processed + 1}_questions.json",
                        cumulative_questions
                    )
                
                total_lectures_processed += 1
                # print(f"✓ Lecture {lecture_idx + 1} complete")
        
        # NEW: Save results to MongoDB
        # print(f"\n{'='*60}")
        # print(f"Saving results to MongoDB...")
        # print(f"{'='*60}")
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        results_data = {
            "lecture_questions": all_lecture_questions,
            "cumulative_questions": all_cumulative_questions,
            "lecture_summaries": all_lecture_summaries,
            "all_previous_lecture_summary": all_previous_lecture_summary,
            "total_lectures_processed": total_lectures_processed,
            "created_at": current_time,
            "updated_at": current_time
        }
        
        qa_document_id = await save_results_to_mongodb(
            course_id=course_id,
            results_data=results_data,
            courses_collection=courses_collection,
            course_question_and_answers_collection=course_question_and_answers_collection
        )
        
        # Cleanup
        await cleanup(all_paths)
        
        # print(f"✓ Results saved to MongoDB with ID: {qa_document_id}")
        # print(f"✓ Course document updated with question_answers_id")
        # print(f"\n{'='*60}")
        # print(f"Processing Complete!")
        # print(f"{'='*60}")
        
        # NEW: Return success response with MongoDB document ID
        return JSONResponse(
            content={
                "message": "Question generation completed successfully",
                "course_id": course_id,
                "question_answers_id": qa_document_id,
                "total_lectures_processed": total_lectures_processed,
                "total_videos": len(videos)
            },
            status_code=200
        )
        
    except Exception as err:
        # print(f"\n Error: {err}")
        try:
            await cleanup(all_paths)
        except:
            pass
        
        return JSONResponse(
            content={"message": "Processing failed", "error": str(err)},
            status_code=500
        )