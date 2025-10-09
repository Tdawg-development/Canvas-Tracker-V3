# Changelog

All notable changes to the Canvas Tracker V3 project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Complete Canvas staging data infrastructure
- `CanvasDataConstructor` class for building structured course data from Canvas API
- Canvas staging data classes: `CanvasCourseStaging`, `CanvasStudentStaging`, `CanvasModuleStaging`, `CanvasAssignmentStaging`
- Interactive demo program (`canvas-staging-demo.ts`) for testing data construction
- Comprehensive Canvas API client with proper array parameter handling

### Fixed
- Canvas API client array parameter handling for `include[]` parameters
- Module items now correctly retrieved with assignments and quizzes
- Proper URL parameter formatting for Canvas API endpoints

### Technical Details
- Fixed `buildUrl()` method in `CanvasClient.ts` to handle array parameters correctly
- Canvas modules API now properly includes items and content details
- Successfully retrieves complete course data including 36 assignments/quizzes from test course

### Performance
- 4 API calls per course data construction
- Average 600ms per API call
- Efficient rate limiting and request management

---

## Project Structure
This changelog tracks the development of Canvas Tracker V3, a system for:
- Staging Canvas LMS data without alteration
- Processing and loading data into database-friendly formats
- Tracking student progress and course analytics