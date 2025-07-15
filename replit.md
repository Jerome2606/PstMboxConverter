# PST to mbox Converter

## Overview

This is a Python command-line application that converts Microsoft Outlook PST (Personal Storage Table) files to the standard mbox format used by many email clients and webmail services. The tool focuses on preserving email metadata, content, and attachments while providing progress feedback and robust error handling.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

### July 2025
- **Critical Bug Fix**: Resolved EmailMessage API conflicts causing 'set_bytes_content() missing maintype' errors
- **Message Creation Rewrite**: Switched from EmailMessage to traditional MIME classes for better reliability
- **PyInstaller Integration**: Added complete executable build system with .bat files and .spec configuration
- **MIT License**: Added proper MIT license to the project
- **Enhanced Documentation**: Updated README with executable build instructions and comprehensive usage examples

### December 2024
- **Library Migration**: Switched from pypff to libratom library for better Python 3 support and maintenance
- **API Updates**: Updated PST parsing logic to use libratom's message iterator and archive interface
- **Documentation**: Enhanced README with comprehensive usage examples and troubleshooting guide
- **Error Handling**: Improved error handling for missing attributes in PST messages using getattr() with defaults

## System Architecture

The application follows a simple, single-purpose architecture:

- **Language**: Python 3.6+
- **Architecture Pattern**: Command-line utility with object-oriented design
- **Main Components**: Single converter class with file processing capabilities
- **Dependencies**: Minimal external dependencies (pypff for PST parsing)

## Key Components

### PSTToMboxConverter Class
- **Purpose**: Core conversion logic and state management
- **Responsibilities**: 
  - Parse PST files using pypff library
  - Convert email data to mbox format
  - Track conversion progress and statistics
  - Handle errors gracefully

### Command-Line Interface
- **Purpose**: Provide user-friendly access to conversion functionality
- **Features**: Argument parsing, help text, and execution flow control

### Logging System
- **Purpose**: Provide feedback during conversion process
- **Features**: Configurable verbosity levels, progress tracking

## Data Flow

1. **Input Processing**: Read and validate PST file using pypff library
2. **Email Extraction**: Traverse PST folder structure and extract individual emails
3. **Format Conversion**: Convert each email to standard mbox format while preserving:
   - Email metadata (sender, recipient, date, subject)
   - Email body content (text and HTML)
   - Attachments
   - Folder structure information
4. **Output Generation**: Write converted emails to mbox file
5. **Progress Tracking**: Provide real-time feedback on conversion progress

## External Dependencies

### libratom Library
- **Purpose**: Parse Microsoft PST files using modern Python interface
- **Installation**: `pip install libratom`
- **Rationale**: Modern, actively maintained library built on top of libpff with better Python 3 support

### Python Standard Library
- **email**: Email message handling and MIME support
- **mailbox**: mbox format creation and manipulation
- **pathlib**: Modern file path handling
- **argparse**: Command-line argument parsing
- **logging**: Progress feedback and error reporting

## Deployment Strategy

### Local Execution
- **Target Environment**: Command-line execution on user's local machine
- **Installation**: Simple pip install for dependencies
- **Usage**: Direct Python script execution with command-line arguments

### Cross-Platform Compatibility
- **Support**: Windows, macOS, and Linux
- **Rationale**: Python's cross-platform nature and pypff library compatibility

## Key Features

### Email Preservation
- **Metadata**: Maintains sender, recipient, date, and subject information
- **Content**: Preserves both plain text and HTML email bodies
- **Attachments**: Handles file attachments properly during conversion

### Performance & Reliability
- **Memory Efficiency**: Designed for processing large PST files without excessive memory usage
- **Error Handling**: Robust error handling for corrupted or invalid files
- **Progress Feedback**: Real-time progress updates during conversion

### File Format Support
- **Input**: Microsoft Outlook PST files
- **Output**: Standard mbox format compatible with most email clients and webmail services

## Development Notes

The application is designed as a single-purpose utility with minimal complexity. The object-oriented design allows for easy extension and modification while maintaining clear separation of concerns. The use of Python's standard library minimizes external dependencies while the pypff library provides the specialized PST parsing capabilities required for the core functionality.