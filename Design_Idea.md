# Wide Events

## Origin
- from web-dev
- (link to the website from django-wide-events)
- collect all information from one request and log at once
- Structured json-logs per request
// Example for its usage

- Better Overview
- Session Traceability: Querying logs from a requets -> Querying request from a user-session
- tail sampling
// Example of tail sampling

## Outside of web-dev
- no direct start-finish like request -> Build Wide Events per Execution
- New concept: Every (major) operation returns a dataclass-result (-> json) //Exact definition is not final
- Logging:
1. Visual: Human-Readable, simple warning, info, cli
2. Log-files: Wide-Events

-> Tree like collection
-> Use EventBlocks as main collection source
// Draw example from example class

## Additional Content

### Simpler Logging Config
-> Directly feeds into the logging
-> Gui (already in termlog)

### Checks
-> Usage of the Results Principle/Concept

### Collectors
-> Direcly used in logging for collection of additional data
-> Follow principle of the django-wide-events
