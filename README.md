# HomoTest

Copyright (c) 2026 Robin Best

HomoTest is the regression test suite for HomoGen. It runs the sample cases under `tests`, compares generated output
against checked-in QA baseline files, and writes a pass/fail summary for the run.

## Repository Layout

- `scripts/HM_Tests.py` - main test runner.
- `scripts/HM_Compare.py` - numeric-aware comparison helpers for text, CSV, and
  image files.
- `tests/config.xml` - global test configuration, product name, tolerances, and
  default executable options.
- `tests/**/HomoGen/qa.xml` - per-case test definitions.
- `tests/**/HomoGen/qa/` - baseline files used for comparisons.
- `tests/summary/` - generated test reports.

## Requirements

- Python 3.
- Built HomoGen mesher and solver executables.
- The test runner must be started with `tests` as the current working
  directory, because it expects to find `config.xml` in the current directory.

On Windows, the VS Code launch configuration in `.vscode/launch.json` uses:

- Mesher: `C:\proj2\HomoGenFreeCAD\install\win64\bin\homo_mesher.exe`
- Solver: `C:\proj2\HomoGenFreeCAD\install\win64\bin\homo_solver.exe`

Adjust these paths if your build output is somewhere else.

## Run All Tests

From the repository root:

```powershell
cd tests
python ..\scripts\HM_Tests.py -verbose `
  -mesher C:\proj2\HomoGenFreeCAD\install\win64\bin\homo_mesher.exe `
  -solver C:\proj2\HomoGenFreeCAD\install\win64\bin\homo_solver.exe
```

The same command is available in VS Code as the debug configuration
`Python: HM_Tests win64`.

## Run Selected Tests

Run only one folder, relative to `tests`:

```powershell
cd tests
python ..\scripts\HM_Tests.py -verbose `
  -folder validation\square `
  -mesher C:\proj2\HomoGenFreeCAD\install\win64\bin\homo_mesher.exe `
  -solver C:\proj2\HomoGenFreeCAD\install\win64\bin\homo_solver.exe
```

Run multiple folders by separating them with commas:

```powershell
python ..\scripts\HM_Tests.py -folder validation\square,validation\box -mesher <path-to-mesher> -solver <path-to-solver>
```

Run a single case by input file name:

```powershell
python ..\scripts\HM_Tests.py -case square_export.json -mesher <path-to-mesher> -solver <path-to-solver>
```

Exclude a folder while running a broader set:

```powershell
python ..\scripts\HM_Tests.py -exclude turbine -mesher <path-to-mesher> -solver <path-to-solver>
```

## Command Options

- `-verbose` - print skipped cases and extra progress information.
- `-folder <folders>` - run only the specified folders. Use paths relative to `tests`; separate multiple folders with commas.
- `-exclude <folder>` - skip the specified folder.
- `-case <input-file>` - run only one case, matched by its `input_file` value in `qa.xml`.
- `-mesher <exe>` - mesher executable to test. Omit to skip mesher runs.
- `-solver <exe>` - solver executable to test. Omit to skip solver runs.
- `-update_qa` - replace QA baseline files with the newly generated outputs.
  Use this only when the new results have been reviewed and are expected.

## Test Configuration

Global settings are read from `tests/config.xml`:

```xml
<test_configuration>
    <product name="HomoGen"/>
    <qa absolute_tol="0.002" relative_tol="0.002" mesher_options="--qa_stats" solver_options="" />
</test_configuration>
```

- `absolute_tol` and `relative_tol` control numeric comparison tolerances.
- `mesher_options` are added to every mesher command.
- `solver_options` are added to every solver command.

Each test folder can define cases in a `qa.xml` file. For example:

```xml
<case input_file="square_export.json">
    <mesher_test options="--surface --input" platform="all">
        <text_compare output="square_mesh/square_edge.stats" gold="qa/square_edge.stats"/>
    </mesher_test>
    <solver_test options="--comp --input" platform="all">
        <text_compare output="square_results/square_comp.json" gold="qa/square_comp.json"/>
    </solver_test>
</case>
```

The runner recursively searches from each requested folder. When it finds a `qa.xml`, it runs the cases in that file, then compares each generated `output` file with its checked-in `gold` file.

## Results

Every run creates a numbered CSV report in `tests/summary`, using this pattern:

```text
<product>_<solver-version>_<date>.<sequence>.csv
```

The latest aggregate summary is also written to:

```text
tests/summary/AD_Tests.csv
```

At the end of a run, the same summary is printed to the terminal with failed and passed cases.

## Updating Baselines

When a solver or mesher change intentionally changes the expected output, run with `-update_qa`:

```powershell
cd tests
python ..\scripts\HM_Tests.py -update_qa `
  -folder validation\square `
  -mesher C:\proj2\HomoGenFreeCAD\install\win64\bin\homo_mesher.exe `
  -solver C:\proj2\HomoGenFreeCAD\install\win64\bin\homo_solver.exe
```

This copies each generated output file over its configured QA baseline. Review the resulting file changes before committing them.
