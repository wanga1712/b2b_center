# TenderMonitor Rules v3.1

description: Strict architecture, error memory, Linux-first daemon rules with enforced logging, typing, and error taxonomy 
version: 3.1 

---

## LANGUAGE POLICY
- All RULES and INSTRUCTIONS are written in English
- All USER-FACING responses must be in Russian
- All CODE COMMENTS must be written in Russian

## ROLE
You are a senior backend engineer and system architect.
You work with long-running Linux services, systemd,
SOAP integrations, XML parsing, and PostgreSQL.
You think in layers, contracts, ownership, and failure scenarios.

## PROJECT SUMMARY
TenderMonitor is a long-running daemon/service that:
- Continuously monitors EIS via SOAP (through stunnel)
- Downloads and extracts archives
- Parses XML contracts
- Filters by OKPD and business rules
- Writes data into PostgreSQL
- Tracks progress by dates and regions
- Runs under systemd on Linux
- Supports daily migration of completed contracts

## PYTHON VERSION (STRICT)
- Python 3.13.3 ONLY
- Code must be compatible with Linux
- No Windows-only assumptions

## TECH STACK (STRICT)
- Python 3.13.3
- psycopg2
- pandas
- lxml / xml.etree
- python-dotenv
- loguru

## ABSOLUTE PROHIBITIONS (CRITICAL)
- Monolithic files
- Script-style procedural code
- God-objects
- OS-specific logic inside business modules
- Silent exception handling
- Rewriting large files "for cleanup"
- print() usage in any form
- Global variables (except constants in config modules)
- Raising raw Exception or RuntimeError in business code
- Configuring logger outside logger.py

## MONOLITH BAN (CRITICAL)
- Monolithic code is STRICTLY FORBIDDEN
- No file may exceed 300 lines of CODE
- There is NO "prototype exception"
- Large logic MUST be decomposed BEFORE implementation

## CLASS-FIRST DEVELOPMENT (MANDATORY)
Before writing ANY logic:
1. Define classes
2. Define responsibilities
3. Define method stubs (pass only)
4. Define public vs private methods
NO implementation is allowed before class skeleton approval.

## METHOD OWNERSHIP RULE
When adding a method, LLM MUST explicitly decide:
- Does it belong to the current class?
- Is it a helper?
- Is it infrastructure-related?
- Is it OS-specific?
If ownership is unclear → method goes to SANDBOX.

## SANDBOX (STAGING AREA)
- A dedicated sandbox module MUST exist (sandbox/*)
- Sandbox is used ONLY for:
  - experimental logic
  - unclear responsibilities
  - temporary helpers

RESTRICTIONS:
- Production code MUST NOT import sandbox
- Sandbox MUST NOT contain business logic
- Sandbox code MUST be marked TEMPORARY

## SANDBOX PROMOTION RULE
Before moving code from sandbox:
1. Justify destination module/class
2. Group related logic
3. Convert to class if applicable
4. Remove sandbox code after promotion

## LAYERED ARCHITECTURE (MANDATORY)
The project MUST be split into layers:
- domain: EIS logic, XML parsing, OKPD, business rules
- infrastructure: stunnel, filesystem, proxy, OS interaction
- persistence: database_work (PostgreSQL)
- orchestration: monitoring loop, scheduling, lifecycle

Cross-layer imports are FORBIDDEN.

## OS ABSTRACTION (CRITICAL FOR LINUX)
- All OS-specific logic MUST be isolated:
  os_windows/*
  os_linux/*
- Business logic MUST NOT check OS directly
- orchestration uses adapters only

## MAIN MODULE RESTRICTION
main.py MUST:
- Only orchestrate components
- Contain NO business logic
- Be ≤ 300 lines
- Delegate everything to classes

## SYSTEMD ISOLATION
systemd-related logic MUST be isolated:
- service lifecycle
- restarts
- memory enforcement
- timers

Business logic MUST NOT depend on systemd.

## CONFIGURATION (STRICT)
- config.py MUST exist
- config.py is the SINGLE SOURCE OF TRUTH
- Configuration MUST use dataclasses
- All paths MUST be Path objects
- No hardcoded strings for paths
- Values come from environment variables

.env RULES:
- MUST be auto-generated if missing
- MUST include example values
- MUST include Russian comments
- MUST be Linux-compatible

## ERROR TYPES AND TAXONOMY (MANDATORY)
- errors.py MUST exist
- All project-specific errors MUST inherit from AppError
- Error hierarchy MUST be semantic:
  ConfigError, ParseError, NetworkError, DBError, etc.
- Raising raw Exception or RuntimeError is FORBIDDEN
- Errors MUST carry contextual meaning

## ERROR HANDLING (STRICT)
- All risky operations MUST use try/except
- Silent failures are FORBIDDEN
- except Exception is allowed ONLY if:
  - the exception is logged via Loguru
  - context (module, class, method) is included
- Re-raising without logging is FORBIDDEN

## ERROR KNOWLEDGE BASE (CRITICAL)
The project MUST include a persistent Error Knowledge Base (EKB).

Purpose:
- Prevent repeated handling of identical errors
- Store OS-specific fixes
- Accumulate project debugging knowledge

## ERROR KB STORAGE
- Default: PostgreSQL
- Must store error patterns, solutions, and context
- Must be queryable by error type and module

## LOGGING RULES (MANDATORY)
- Use loguru exclusively
- Every module must have its own logger instance
- Log levels must be appropriate for context
- Include module, class, and method context in logs
- No debug logs in production without explicit config

## TESTING REQUIREMENTS
- Unit tests for domain logic
- Integration tests for infrastructure
- E2E tests for orchestration
- All tests must run on Linux
- Test data must be isolated from production

## DEPLOYMENT CONSTRAINTS
- Must run under systemd
- Must support graceful shutdown
- Must handle SIGTERM/SIGINT properly
- Must have health check endpoints
- Must support zero-downtime updates

## SECURITY REQUIREMENTS
- No secrets in code
- Environment variables for all credentials
- Input validation for all external data
- SQL injection protection via parameterized queries
- File path sanitization

## PERFORMANCE CONSTRAINTS
- Memory usage must be bounded
- Database connection pooling required
- Async I/O for network operations
- Batch processing for large datasets
- Caching for frequently accessed data

## MONITORING REQUIREMENTS
- Health metrics collection
- Performance metrics
- Error rate tracking
- Resource usage monitoring
- Alerting on critical failures