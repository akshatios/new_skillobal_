import uuid
import shutil
import asyncio
from pathlib import Path
from datetime import datetime
from langchain_xai import ChatXAI
from core.config import ai_api_secrets
from langchain_openai import ChatOpenAI
from fastapi import Request, Form, Depends
from fastapi.responses import JSONResponse
from langchain_core.runnables import RunnableParallel
from langchain_google_genai import ChatGoogleGenerativeAI
from helper_function.apis_requests import get_current_user
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.runnables.passthrough import RunnableAssign
from core.database import courses_collection, courses_videos_collection
from helper_function.ai_feature_helper_function.runnable_lambda import extract_summary, extract_questions

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
    audio_to_text,
    video_to_audio, 
    save_text_to_pdf,
    sanitize_question_dict
)
from helper_function.ai_feature_helper_function.mongodb_helper import (
    chunk_videos,
    save_video_results,
    cleanup_batch_files,
    download_video_from_url,
    fetch_course_videos_with_questions
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
            # "anthropic": ChatOpenAI(model="gpt-5.1-2025-11-13"),
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
        
        all_paths = {
            "base_dir": base_dir,
            "data_dir": data_dir,
            "font_path": base_dir / "helper_function" / "ai_feature_helper_function" /"font" / "Poppins-Regular.ttf"
        }
        
        # Create base data directory
        await asyncio.to_thread(data_dir.mkdir, exist_ok=True, parents=True)
        
        return all_paths
    except Exception as err:
        raise Exception(f"Path creation failed: {err}")

async def create_batch_paths(base_data_dir: Path, batch_idx: int):
    """Create paths for a specific batch to isolate memory usage"""
    batch_dir = base_data_dir / f"batch_{batch_idx}"
    
    batch_paths = {
        "batch_dir": batch_dir,
        "input_video_dir": batch_dir / "input_video",
        "input_audio_dir": batch_dir / "input_audio",
        "input_text_dir": batch_dir / "input_text",
        "input_pdf_dir": batch_dir / "input_pdf",
        "split_pdf_dir": batch_dir / "split_pdf"
    }
    
    # Create all directories
    for path in batch_paths.values():
        await asyncio.to_thread(path.mkdir, exist_ok=True, parents=True)
    
    return batch_paths

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

async def process_single_video(
    video_doc: dict,
    video_idx_in_batch: int,
    global_video_idx: int,
    batch_paths: dict,
    font_path: Path,
    summary_chain,
    number_of_questions: int,
    hinglish: bool
) -> tuple:
    """Process a single video to generate summaries"""
    try:
        video_id = str(video_doc["_id"])
        video_url = video_doc.get("videoUrl")
        video_title = video_doc.get("video_title", f"Video {global_video_idx + 1}")
        
        if not video_url:
            raise Exception(f"No videoUrl found for video {video_title}")
        
        # Download video
        video_target = batch_paths["input_video_dir"] / f"video_{video_idx_in_batch}.mp4"
        await download_video_from_url(video_url, video_target)
        
        # Convert to audio
        audio_target = batch_paths["input_audio_dir"] / f"video_{video_idx_in_batch}.mp3"
        await video_to_audio(video_target, output_path=audio_target)
        
        # Transcribe
        text_file_path = batch_paths["input_text_dir"] / f"video_{video_idx_in_batch}.txt"
        await audio_to_text(
            path=audio_target,
            text_file_path=text_file_path,
            hinglish=hinglish
        )
        
        # Convert to PDF
        pdf_path = batch_paths["input_pdf_dir"] / f"video_{video_idx_in_batch}.pdf"
        await save_text_to_pdf(
            text_file_path=text_file_path,
            output_path=pdf_path,
            font_path=font_path
        )
        
        # Split PDF into pages
        video_split_dir = batch_paths["split_pdf_dir"] / f"video_{video_idx_in_batch}"
        await asyncio.to_thread(video_split_dir.mkdir, parents=True, exist_ok=True)
        total_pages = await split_pdf(pdf_path, video_split_dir)
        
        # Process each page
        cumulative_concise = ""
        cumulative_detailed = ""
        
        for page_num in range(total_pages):
            concise, detailed = await process_single_page(
                page_num=page_num,
                split_pdf_dir=video_split_dir,
                previous_pages_summary=cumulative_concise,
                summary_chain=summary_chain,
                number_of_questions=number_of_questions
            )
            cumulative_concise += concise
            cumulative_detailed += detailed
        
        return video_id, video_title, cumulative_concise, cumulative_detailed
        
    except Exception as err:
        raise Exception(f"Video processing failed for {video_doc.get('video_title', 'unknown')}: {err}")

async def cleanup(all_paths):
    """Clean up temporary files"""
    try:
        if all_paths["data_dir"].exists():
            await asyncio.to_thread(shutil.rmtree, all_paths["data_dir"])
    except Exception as err:
        pass  # Ignore cleanup errors

async def QuestionAnswerGenerationModel(
    request: Request, 
    token: str = Depends(get_current_user), 
    course_id: str = Form(...),
    number_of_questions: int = Form(...),
    hinglish: bool = Form(...)
):
    """
    UNIFIED API for question generation - handles both new courses and adding new videos.
    
    CASES HANDLED:
    1. New Course: All videos need questions (start_idx = 0, no previous summary)
    2. Adding at End: [v1✓, v2✓, v3✓, v4✓, v5, v6] (start_idx = 4)
    3. Adding in Between: [v1✓, v1.1, v1.2, v2✓, v3✓] (start_idx = 1, regenerate v2, v3)
    4. Adding at Beginning: [v0.1, v0.2, v1✓, v2✓] (start_idx = 0, regenerate all)
    5. Mixed: Any combination of above
    
    LOGIC:
    - Find first video WITHOUT questions
    - Use previous video's cumulative_summary_up_to_here (or "" if none)
    - Generate questions from that point to the end
    - Regenerate questions for videos that come after (even if they had questions)
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
        
        # Fetch videos and identify which need processing
        (
            all_videos, 
            skipped_items, 
            last_video_with_questions, 
            first_idx_without_questions
        ) = await fetch_course_videos_with_questions(
            course_id=course_id,
            courses_collection=courses_collection,
            courses_videos_collection=courses_videos_collection
        )
        
        if not all_videos:
            return JSONResponse(
                content={"message": "No valid video ObjectIds found for this course"},
                status_code=200
            )
        
        # Determine processing range
        if first_idx_without_questions == -1:
            # All videos already have questions
            return JSONResponse(
                content={
                    "message": "All videos already have questions generated",
                    "total_videos": len(all_videos)
                },
                status_code=200
            )
        
        # Get starting cumulative summary
        if last_video_with_questions:
            starting_cumulative_summary = (
                last_video_with_questions
                .get("ai_generated_content", {})
                .get("cumulative_summary_up_to_here", "")
            )
        else:
            starting_cumulative_summary = ""
        
        # Videos to process: from first_idx_without_questions to end
        videos_to_process = all_videos[first_idx_without_questions:]
        
        # Split into batches of 5
        video_batches = chunk_videos(videos_to_process, batch_size=5)
        
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
        
        # Tracking variables
        current_cumulative_summary = starting_cumulative_summary
        total_videos_processed = 0
        processed_video_ids = []
        
        # Calculate global video indices (relative to ALL videos in course)
        start_global_idx = first_idx_without_questions
        
        # Process each batch
        for batch_idx, batch_videos in enumerate(video_batches):
            # Create batch-specific paths
            batch_paths = await create_batch_paths(all_paths["data_dir"], batch_idx)
            
            # Store paths to clean up after batch
            batch_cleanup_paths = [batch_paths["batch_dir"]]
            
            try:
                # Process each video in batch
                for video_idx_in_batch, video_doc in enumerate(batch_videos):
                    global_video_idx = start_global_idx + total_videos_processed
                    
                    # Process video to get summaries
                    video_id, video_title, concise_summary, detailed_summary = await process_single_video(
                        video_doc=video_doc,
                        video_idx_in_batch=video_idx_in_batch,
                        global_video_idx=global_video_idx,
                        batch_paths=batch_paths,
                        font_path=all_paths["font_path"],
                        summary_chain=summary_chain,
                        number_of_questions=number_of_questions,
                        hinglish=hinglish
                    )
                    
                    # Generate individual questions (based on this video only)
                    individual_questions = await generate_questions_for_lecture(
                        lecture_summary=detailed_summary,
                        question_generation_chain=question_generation_chain,
                        question_selection_chain=question_selection_chain,
                        number_of_questions=number_of_questions
                    )
                    
                    # Update cumulative summary
                    if current_cumulative_summary == "":
                        # First video in processing range
                        current_cumulative_summary = concise_summary
                        cumulative_questions = individual_questions  # For consistency
                        cumulative_summary_up_to_here = concise_summary
                    else:
                        # Subsequent videos: combine with previous summaries
                        cumulative_result = await cumulative_summary_chain.ainvoke({
                            "previous_lectures_summary": current_cumulative_summary,
                            "new_lecture_summary": concise_summary,
                            "lecture_number": global_video_idx + 1
                        })
                        cumulative_summary_up_to_here = cumulative_result["combined_summary"]
                        current_cumulative_summary = cumulative_summary_up_to_here
                        
                        # Generate cumulative questions
                        cumulative_questions = await generate_questions_for_lecture(
                            lecture_summary=cumulative_summary_up_to_here,
                            question_generation_chain=question_generation_chain,
                            question_selection_chain=question_selection_chain,
                            number_of_questions=number_of_questions
                        )
                    
                    # Save to MongoDB
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    video_data = {
                        "individual_questions": individual_questions,
                        "cumulative_questions": cumulative_questions,
                        "concise_summary": concise_summary,
                        "detailed_summary": detailed_summary,
                        "cumulative_summary_up_to_here": cumulative_summary_up_to_here,
                        "processed_at": current_time
                    }
                    
                    await save_video_results(
                        video_id=video_id,
                        video_data=video_data,
                        courses_videos_collection=courses_videos_collection
                    )
                    
                    processed_video_ids.append(video_id)
                    total_videos_processed += 1
                
            finally:
                # Clean up batch files to free RAM
                await cleanup_batch_files(batch_cleanup_paths)
        
        # Final cleanup
        await cleanup(all_paths)
        
        return JSONResponse(
            content={
                "message": "Question generation completed successfully",
                "course_id": course_id,
                "total_videos_in_course": len(all_videos),
                "videos_processed": total_videos_processed,
                "processed_video_ids": processed_video_ids,
                "started_from_index": first_idx_without_questions,
                "skipped_items": skipped_items if skipped_items else None,
                "had_previous_questions": last_video_with_questions is not None
            },
            status_code=200
        )
        
    except Exception as err:
        try:
            await cleanup(all_paths)
        except:
            pass
        
        return JSONResponse(
            content={"message": "Processing failed", "error": str(err)},
            status_code=500
        )