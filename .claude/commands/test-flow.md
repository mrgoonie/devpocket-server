---
description: Run test flows and fix issues
---

Run `./scripts/run-tests.sh` to test all the flows of this system and fix any issues that arise follow the workflow below:

## Notes
- The test might take a long time to finish, set your command timeout to at least 15 minutes

## Workflow
You must follow this workflow strictly:
- start with the `project-orchestrator` to review the issues and provide a fix plan
- proceed to implement with `backend-system-architect`, when the implementation is finished, test again to make sure everything work properly
- if there are any other issues, use `expert-debugger` to debug and fix them.
- when everything is done, use `project-orchestrator` to review the implementation
- if the user is satisfied, use `api-docs-specialist` to update the API documentation and use `project-orchestrator` to close the task
- finally use `project-orchestrator` to commit and push all the code
