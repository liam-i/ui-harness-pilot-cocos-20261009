## ADDED Requirements

### Requirement: Menu and session transitions preserve approved behavior

The application SHALL implement the approved menu, reset dialog and static session preview without adding full game play or persistence.

#### Scenario: Cold start and disabled continuation

- **WHEN** the process is cold-started
- **THEN** best is 128, no session exists, and Continue is disabled; touching it does not create a session

#### Scenario: New session and continuation

- **WHEN** New game is touched, Menu is touched, and Continue is touched
- **THEN** the same session is resumed with the approved static 2/2 preview; New game remains available to create a new session

#### Scenario: Reset or cancel with and without a session

- **WHEN** Reset best score opens a dialog
- **THEN** outside touches are blocked and Cancel preserves best and session; Reset sets best to zero without discarding an existing session
- **AND** without a session Continue remains disabled; with a session Continue resumes it; these rules also hold when best was already zero

### Requirement: Android lifecycle and configuration match the approved scope

The application SHALL preserve in-process state, implement contextual Android Back, and retain the approved portrait canvas on both selected simulators.

#### Scenario: Contextual Back

- **WHEN** Android Back is used in a dialog, session, or root menu
- **THEN** it respectively cancels the dialog, returns to the resumable menu, or leaves the foreground; a later cold start returns to the initial state

#### Scenario: Home and resume

- **WHEN** Home is used with best zero and an existing session, then the still-running process resumes
- **THEN** screen, best and session remain unchanged

#### Scenario: Font scale and orientation

- **WHEN** font_scale is 1.3 or landscape is requested
- **THEN** the game canvas retains its approved font sizes, remains portrait, and keeps controls and text complete within the actual safe area
- **AND** tests restore the dedicated device settings afterwards

### Requirement: Native presentation consumes the exact approved resources

The application SHALL load the approved PNGs and tokens through Cocos resources, with traceable Scene, SpriteFrame and UUID mappings.

#### Scenario: Seven states and resource identity

- **WHEN** the seven approved states and applicable best-zero dialog variants are reached through real user input
- **THEN** resources match D, actual controls obey the approved dimensions and spacing, and reference/runtime evidence permits only the three recorded differences
- **AND** no required resource depends on a live design tool or the active Change directory at runtime

### Requirement: Verification rejects missing or unsuccessful obligations

The delivery SHALL retain fixed identities and require all C01–C16 cases on both devices, actual platform CI, and the original human gates.

#### Scenario: Successful local and CI execution

- **WHEN** validation succeeds
- **THEN** the result contains both exact device identities, 32 distinct device/case outcomes, current A/D observations, code and APK hashes, resource mappings, screenshots, commands and exit codes

#### Scenario: Missing input or platform execution failure

- **WHEN** an approved input is missing or stale, or a required build/test is failed, skipped, cancelled, timed out, missing or reports zero cases
- **THEN** the applicable gate rejects delivery and retains diagnostics
- **AND** a corrected run obtains new evidence without deleting the failure, changing D/A or reducing the denominator

#### Scenario: Design tool unavailable

- **WHEN** the design production service is stopped
- **THEN** the approved package and history remain independently recoverable and the consumer uses those fixed objects
