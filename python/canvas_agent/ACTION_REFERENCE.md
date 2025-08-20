# CanvasAgent Actions

Generated action reference (do not edit manually).

## add_module_item

Add an item (assignment/page/file) to a module

**Parameters:**

- `course_id` (required) - 
- `module_id` (required) - 
- `title` (required) - 
- `type` (required) - 
- `content_id` (optional) - 

## attach_rubric

Attach existing rubric to an assignment or quiz

**Parameters:**

- `course_id` (required) - Course ID
- `rubric_id` (required) - Rubric ID
- `association_id` (required) - Assignment or Quiz ID
- `association_type` (optional) - Assignment or Quiz

## create_announcement

Create an announcement

**Parameters:**

- `course_id` (required) - 
- `title` (required) - 
- `message` (required) - 

## create_assignment

Create an assignment (also used for lightweight quizzes)

**Parameters:**

- `course_id` (required) - Course ID
- `name` (required) - Assignment name
- `description` (optional) - HTML description
- `points_possible` (optional) - Points (default 100)
- `due_at` (optional) - ISO8601 due date

## create_module

Create a module

**Parameters:**

- `course_id` (required) - Course ID
- `name` (required) - Module name

## create_page

Create a wiki page

**Parameters:**

- `course_id` (required) - 
- `title` (required) - 
- `body` (optional) - 

## create_quiz

Create a real (graded) quiz (Classic)

**Parameters:**

- `course_id` (required) - Course ID
- `name` (required) - Quiz title
- `description` (optional) - HTML description
- `points_possible` (optional) - Points (sum of questions)
- `due_at` (optional) - Due date ISO
- `question` (optional) - Single question text (auto add)
- `answers` (optional) - List of answers (first correct if provided)
- `rubric_criteria` (optional) - List of {description, points}

## create_quiz_question

Add a question to an existing quiz

**Parameters:**

- `course_id` (required) - Course ID
- `quiz_id` (required) - Quiz ID
- `question` (required) - Question text
- `answers` (optional) - Answers (first treated correct)

## create_rubric

Create a rubric with criteria

**Parameters:**

- `course_id` (required) - Course ID
- `title` (required) - Rubric title
- `criteria` (optional) - List of {description, points}

## get_course_info

Get high level info for a course

**Parameters:**

- `course_id` (required) - Canvas course numeric ID

## get_user_profile

Get profile for current or specified user

**Parameters:**

- `user_id` (optional) - 

## list_announcements

List announcements

**Parameters:**

- `course_id` (required) - 

## list_assignments

List assignments for a course

**Parameters:**

- `course_id` (required) - Course ID

## list_courses

List courses for the authenticated teacher

_No parameters._

## list_files

List course files

**Parameters:**

- `course_id` (required) - 

## list_module_items

List items in a module

**Parameters:**

- `course_id` (required) - Course ID
- `module_id` (required) - Module ID

## list_modules

List modules in a course

**Parameters:**

- `course_id` (required) - Course ID

## list_pages

List wiki pages

**Parameters:**

- `course_id` (required) - 

## list_rubrics

List rubrics for a course

**Parameters:**

- `course_id` (required) - Course ID

## list_students

List students enrolled

**Parameters:**

- `course_id` (required) - 

## publish_course

Publish a course (make it available to students)

**Parameters:**

- `course_id` (required) - Canvas course numeric ID

Requires confirmation before execution.

## unpublish_course

Unpublish a course (withdraw offering)

**Parameters:**

- `course_id` (required) - Canvas course numeric ID

Requires confirmation before execution.

## update_assignment

Update basic assignment fields (name, description, due date)

**Parameters:**

- `course_id` (required) - Course ID
- `assignment_id` (required) - Assignment ID
- `name` (optional) - New name
- `description` (optional) - New description
- `due_at` (optional) - New due date ISO

## upload_file

Upload a local file to the course

**Parameters:**

- `course_id` (required) - 
- `filepath` (required) - Relative or absolute path to file

