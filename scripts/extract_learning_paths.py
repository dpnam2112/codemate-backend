#!/usr/bin/env python3

from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from core.db import session_context
from core.db.session import DB_MANAGER, Dialect
from machine.models import (
    LearningPaths,
    RecommendLessons,
    StudentCourses,
)
import json
import asyncio
from core.logger import syslog
import argparse
from uuid import UUID
from pathlib import Path

async def extract_learning_paths_data(
    course_id: Optional[UUID] = None,
    student_id: Optional[UUID] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract learning paths data from the database for evaluation.
    
    Args:
        course_id: Optional UUID to filter by specific course
        student_id: Optional UUID to filter by specific student
        start_date: Optional date string (YYYY-MM-DD) to filter paths after this date
        end_date: Optional date string (YYYY-MM-DD) to filter paths before this date
    
    Returns:
        Dict containing structured learning paths data
    """
    try:
        async with session_context(DB_MANAGER[Dialect.POSTGRES]) as session:
            # Build base query
            query = (
                select(LearningPaths)
                .options(
                    joinedload(LearningPaths.student),
                    joinedload(LearningPaths.course),
                    joinedload(LearningPaths.recommend_lessons)
                    .joinedload(RecommendLessons.lesson),
                    joinedload(LearningPaths.recommend_lessons)
                    .joinedload(RecommendLessons.modules)
                )
            )
            
            # Apply filters
            if course_id:
                query = query.where(LearningPaths.course_id == course_id)
            if student_id:
                query = query.where(LearningPaths.student_id == student_id)
            if start_date:
                query = query.where(LearningPaths.start_date >= start_date)
            if end_date:
                query = query.where(LearningPaths.end_date <= end_date)
            
            syslog.info("Executing database query...")
            result = await session.execute(query)
            learning_paths = result.unique().scalars().all()
            syslog.info(f"Found {len(learning_paths)} learning paths")
            
            # Process learning paths
            paths_data = []
            
            for path in learning_paths:
                # Get issues summary from StudentCourses
                student_course_query = (
                    select(StudentCourses)
                    .where(
                        StudentCourses.student_id == path.student_id,
                        StudentCourses.course_id == path.course_id
                    )
                )
                student_course_result = await session.execute(student_course_query)
                student_course = student_course_result.scalar_one_or_none()
                
                # Process recommended lessons
                lessons_data = []
                
                for rec_lesson in sorted(path.recommend_lessons, key=lambda x: x.order or 0):
                    # Process modules for this lesson
                    modules_data = []
                    for module in rec_lesson.modules:
                        modules_data.append({
                            "id": str(module.id),
                            "title": module.title,
                            "objectives": module.objectives,
                        })
                    
                    lessons_data.append({
                        "id": str(rec_lesson.id),
                        "order": rec_lesson.order,
                        "lesson": {
                            "id": str(rec_lesson.lesson.id) if rec_lesson.lesson else None,
                            "title": rec_lesson.lesson.title if rec_lesson.lesson else None,
                            "description": rec_lesson.lesson.description if rec_lesson.lesson else None
                        },
                        "explanation": rec_lesson.explain,
                        "modules": modules_data
                    })
                
                # Compile path data
                path_data = {
                    "id": str(path.id),
                    "student": {
                        "id": str(path.student.id),
                        "email": path.student.email
                    },
                    "course": {
                        "id": str(path.course.id),
                        "name": path.course.name,
                        "description": path.course.description if hasattr(path.course, 'description') else None
                    },
#                    "course_issues": {
#                        "issues_summary": student_course.issues_summary if student_course else None
#                    },
                    "metadata": {
                        "version": path.version,
                        "start_date": path.start_date.isoformat() if path.start_date else None,
                        "end_date": path.end_date.isoformat() if path.end_date else None,
                        "objective": path.objective,
                        # "llm_response": path.llm_response
                    },
                    "recommended_lessons": lessons_data
                }
                paths_data.append(path_data)
                syslog.info(f"Processed learning path {path.id}")
            
            return {
                "learning_paths": paths_data,
                "metadata": {
                    "total_paths": len(paths_data),
                    "extraction_date": datetime.utcnow().isoformat(),
                    "filters_applied": {
                        "course_id": str(course_id) if course_id else None,
                        "student_id": str(student_id) if student_id else None,
                        "start_date": start_date,
                        "end_date": end_date
                    }
                }
            }
    except Exception as e:
        syslog.error(f"Error extracting learning paths: {str(e)}")
        raise

def validate_date(date_str: str) -> str:
    """Validate date string format (YYYY-MM-DD)"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")

def validate_uuid(uuid_str: str) -> UUID:
    """Validate UUID string format"""
    try:
        return UUID(uuid_str)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid UUID format: {uuid_str}")

async def main():
    """
    Main function to handle CLI arguments and run the extraction.
    """
    parser = argparse.ArgumentParser(
        description="Extract learning paths data for evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all learning paths
  python extract_learning_paths.py
  
  # Extract learning paths for a specific course
  python extract_learning_paths.py --course-id 123e4567-e89b-12d3-a456-426614174000
  
  # Extract learning paths for a specific student
  python extract_learning_paths.py --student-id 123e4567-e89b-12d3-a456-426614174001
  
  # Extract learning paths within a date range
  python extract_learning_paths.py --start-date 2024-01-01 --end-date 2024-03-24
  
  # Combine filters and specify output file
  python extract_learning_paths.py --course-id 123e4567-e89b-12d3-a456-426614174000 --output path_data.json
        """
    )
    
    parser.add_argument(
        '--course-id',
        type=validate_uuid,
        help='Filter by course UUID'
    )
    parser.add_argument(
        '--student-id',
        type=validate_uuid,
        help='Filter by student UUID'
    )
    parser.add_argument(
        '--start-date',
        type=validate_date,
        help='Filter paths after this date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end-date',
        type=validate_date,
        help='Filter paths before this date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='learning_paths_evaluation.json',
        help='Output JSON file path (default: learning_paths_evaluation.json)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    try:
        syslog.info("Starting learning paths extraction...")
        data = await extract_learning_paths_data(
            course_id=args.course_id,
            student_id=args.student_id,
            start_date=args.start_date,
            end_date=args.end_date
        )
        
        # Create output directory if it doesn't exist
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save the data
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        syslog.info(f"Successfully extracted {data['metadata']['total_paths']} learning paths")
        syslog.info(f"Data saved to {output_path}")
        
    except Exception as e:
        syslog.error(f"Failed to extract learning paths: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 
