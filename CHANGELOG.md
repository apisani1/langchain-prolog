# Changelog
## [0.1.1.post8] - 2025-05-26

 ### Changes
- Add poetry cache to tests and release workflows



## [0.1.1.post7] - 2025-05-26

 ### Changes
- Replace Makefile with run.sh bash script and migrate github workflows to use it for a single source of truth
- Add linting and formating to tests workflow
- Separate test workflow from release
- Add makefile actions to create and remove jupiter notebook kernels
- Correct mock settings for documentation
- Correct GitHub PR request endpoint
- Update RTD endpoint for sync versions
- Delete annoucement
- Reformat conf.py to test documentation workflow
- Add documentation checks
- Activate TestPyPI for all releases
- Add PR comment in docs workflow


## [0.1.1.post6] - 2025-05-18

 ### Changes
- Correct RTD trigger in release workflow



## [0.1.1.post5] - 2025-05-18

 ### Changes
- Correct RTD trigger in release workflow



## [0.1.1.post4] - 2025-05-18

 ### Changes
- Correct RTD trigger in release workflow



## [0.1.1.post3] - 2025-05-18

 ### Changes
- Correct RTD trigger in release workflow



## [0.1.1.post2] - 2025-05-18

 ### Changes
- Correct release-type check on release workflow
- Correct Update ReadTheDocs workflow version prompt



## [0.1.1.post1] - 2025-05-18

 ### Changes
- Solve version handling issue with RTD workflow


## v0.1.1 - 2025-05-17

 ### Changes
- Overide run definition in Prolog Tool to allow passing a pydantic model
- Update doc project files
- Update Makefiles for release management script and other CLI tools
- Update release workflow to use tag messages for release notes
- Redesign release management script
- Transition formatting and linting configuration to pyproject.toml


## [0.1.0.post1] - 2025-03-07

### Changed
- Fixed repository and release links in package metadata

## [0.1.0] - 2025-02-13

### Initial Release
* Initial version of langchain-prolog
* Basic Prolog integration with LangChain
* Support for Prolog queries as runnables and tools
