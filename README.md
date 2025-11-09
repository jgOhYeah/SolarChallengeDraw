# Solar challenge race draw
A programme for generating and managing a double elimination draw for a model solar car race.
This is a work in progress.



## Installation and setup.
### Prerequisites
- Install the [python](https://www.python.org/) interpretor if not already installed (Tested with 3.12, minimum is 3.10).
- To export PDFs, [Ghostscript](https://ghostscript.com/) is required.
- A [git](https://git-scm.com/) client is highly recommended to download the code, perform version management and keep it up to date.
- A text editor (like [vscode](https://code.visualstudio.com/)) is highly recommended.

### Obtaining the code and virtual environment setup
- Open a terminal and change working directory to a folder where this project is to be located.
- Clone this repository using git.
    ```bash
    git clone <REPOSITORY URL>
    ```
    <!-- TODO -->
- Change working directory to the newly created folder.
    ```bash
    cd SolarChallengeDraw
    ```
- Create a python virtual environment. This will store the libraries required to run this project in their own folder rather than as part of the system's libraries. This is optional, but doing so avoids possible conflicts and issues with other projects.
    ```bash
    python[3] -m venv .venv
    ```
    > ![TIP]
    > Depending on the operating system and computer, the python interpretor may either be known as `python` (common for Windows) or `python3` (common for Linux)
- Once the virtual environment has been created, it now needs to be activated so that the computer uses it instead of the system environment. The exact command varies between operating systems.
    - Windows command prompt:
        ```cmd
        .venv\Scripts\activate
        ```
    - Windows powershell:
        ```ps1
        .venv\Scrips\Activate.ps1
        ```
        You may need to [allow scripts to run](https://dev.to/aka_anoop/enabling-virtualenv-in-windows-powershell-ka3) using:
        ```ps1
        Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope CurrentUser
        ```
    - Linux and macOS:
        ```bash
        source .venv/bin/activate
        ```
    Once activated, the terminal prompt should begin with `(.venv)`.
- Install the required python libraries by running:
    ```bash
    pip[3] install -r requirements.txt
    ```
    > ![TIP]
    > Again, this may be `pip` or `pip3` depending on the computer.

### Running the programme
> ![NOTE]
> This is still a work in progress and will change.

- If the terminal has been closed since the virtual environment was last activated, change working directory (`cd`) to the `SolarChallengeDraw` folder and activate it.
- Run the tool using:
    ```bash
    python[3] ./app/main.py --cars=database/cars.csv
    ```
    Where `database/cars.csv` is a csv file that contains a list of cars.

## Cars CSV file
> ![NOTE]
> This is still a work in progress and will change.

For example:

| Car ID | School ID | Car name | Scruitineered | Present for round robin | Present for knockout | Points |
|:-:|:-:| - |:-:| - | - | - |
| 401 | 1 | School 1, car 401 | | | | 1 |
| 402 | 1 | School 1, car 402 | | | | 3 |
| 403 | 2 | School 2, car 403 | | | | 2 |
| 404 | 3 | School 3, car 404 | | | | 1 |