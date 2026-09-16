import click, os, subprocess, json, re, ast, io
from pyflakes.api import check
from pyflakes.reporter import Reporter
from pathlib import Path

# Control-flow node types that add a decision point / nesting level
NESTING_NODES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith)
FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
 
SKIP_DIRS = {".git", "__pycache__", "venv", ".venv", "node_modules"}
language_map = {
    "py":  "Python",
    "js":  "JavaScript",
    "java": "Java",
    "cpp": "C++",
    "c":   "C",
    "rb":  "Ruby",
    "php": "PHP",
    "go":  "Go",
    "rs":  "Rust"
}

# Commands
@click.command()
@click.option('-i','--directory',  type=click.Path(exists=True, file_okay=False,dir_okay=True),help='provides basic info on the directory')
@click.option("-s","--project", type=click.Path(exists=True, file_okay=False, dir_okay=True),help='provides basic info on the size of files in directory')
@click.option("-g","--git", type=click.Path(exists=True, file_okay=False, dir_okay=True),help='provides git info on directory')
@click.option("-a","--dir", type=click.Path(exists=True, file_okay=False, dir_okay=True),help='analyzes dependencies on given directory')
@click.option("-h","--health", type=click.Path(exists=True, file_okay=False, dir_okay=True),help='provides health check on given directory')
@click.option("-t","--test", type=click.Path(exists=True, file_okay=False, dir_okay=True),help='analyzes code metrics of a directory')
def cli(directory,project,git,dir,health,test):
    if directory:
        printStats(directory)

    if project:
        sizeOf(project)

    if git:
        gitInfo(git)
    if dir:
        analyzeDep(dir)

    if health:
        healthCheck(health)
    if test:
        analyzeComp(test)


#Version 1
def printStats(directory):
    click.echo("Overview")
    click.echo("----------")
    click.echo(f"Project:{Path(directory).resolve().name}")
    click.echo(f"Root Directory:{os.path.abspath(directory)}")
    click.echo("")
    countFilesAndDirs(directory)
    click.echo(f"Empty Files:{emptyFiles(directory)}")
    click.echo(f"Duplicate Files:{dupFiles(directory)}")
    click.echo("")

    lang(directory)
    if hasGit(directory):
        click.echo("Git Repository: Yes")
    else:
        click.echo("Git Repository: No")
#Version 2
def sizeOf(project):
    click.echo("Lines of Code")
    click.echo("-------------")
    countLangFiles(project)
#Version 3
def gitInfo(git):
    if not hasGit(git):
        click.echo(f"{git} is not a git repository")
        return
    click.echo("Git Status")
    click.echo("----------")
    #Current Branch
    branch=gitRun(["rev-parse", "--abbrev-ref", "HEAD"], git)
    #Files
    modified=gitRun(["diff","--name-only"], git)
    untracked = gitRun(["ls-files", "--others", "--exclude-standard"], git)
    staged = gitRun(["diff", "--cached", "--name-only"], git)

    #Commit
    commit_raw = gitRun(["log", "-1", "--pretty=format:%H%n%an%n%ad%n%s"],git)
    commit_parts = commit_raw.split("\n") if commit_raw else []
    commit = {
        "author": commit_parts[1] if len(commit_parts) > 1 else None,
        "date": commit_parts[2] if len(commit_parts) > 2 else None,
        "message": commit_parts[3] if len(commit_parts) > 3 else None,
    }
    
    
    click.echo(f"Current Branch: {branch}")
    click.echo()
    click.echo("Files")
    click.echo("-----------")
    modifiedFiles=modified.split('\n') if modified else []
    untrackedFiles=untracked.split('\n') if untracked else []
    stagedFiles=staged.split('\n') if staged else []
    click.echo(f"Modified:{modifiedFiles}")
    click.echo(f"Untracked:{untrackedFiles}")
    click.echo(f"Staged:{stagedFiles}")

    click.echo()
    click.echo("Last Commit")
    click.echo("-----------")
    click.echo(f"Author: {commit['author']}")
    click.echo(f"Date: {commit['date']}")
    click.echo(f"Message: {commit['message']}")

#Version 4


def analyzeDep(dir):
    pkgPath = ""
    for path, dirs, files in os.walk(dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        if "package.json" in files:
            pkgPath = os.path.join(path, "package.json")
            break

    if not pkgPath:
        raise click.ClickException(f"No package.json found under {dir}")

    try:
        with open(pkgPath, "r") as f:
            pkgJSON = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise click.ClickException(f"Could not read {pkgPath}: {e}")

    deps = pkgJSON.get("dependencies", {})
    devDeps = pkgJSON.get("devDependencies", {})
    click.echo("Dependencies")
    click.echo("------------")
    click.echo(f"Production: {len(deps)}, {deps}")
    click.echo(f"Development: {len(devDeps)}, {devDeps}")
    click.echo()
    click.echo("Largest Packages")
    click.echo("----------------")

    nodePath = ""
    for path, dirs, files in os.walk(dir):
        if "node_modules" in dirs:
            nodePath = os.path.join(path, "node_modules")
            break

    if not nodePath:
        click.echo("(node_modules not found - run npm install to see installed package sizes)")
        return

    all_deps = {**deps, **devDeps}
    sizes = {}
    for pkg in all_deps:
        pkgpath = os.path.join(nodePath, pkg)
        if os.path.isdir(pkgpath):
            sizes[pkg] = folder_size(pkgpath)

    if not sizes:
        click.echo("(none of the declared dependencies are installed in node_modules)")
        return

    for pkg, size in sorted(sizes.items(), key=lambda x: x[1], reverse=True)[:5]:
        click.echo(f"{pkg}: {size / 1024:.1f} KB")
    

#Version 6
def healthCheck(dir):
    click.echo("Project Health")
    click.echo("---------------")
    fileCheck(dir)

#Version 7
def analyzeComp(dir):
    """Analyze function-level code metrics for all .py files under DIRECTORY."""
    results = {"lengths": [], "complexities": [], "nestings": [], "warnings": 0, "files_scanned": 0}
 
    for root, dirs, files in os.walk(dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                # click.echo(f"scanning {filepath}")
                analyze_file(filepath, results)
 
    if not results["lengths"]:
        click.echo("No functions found.")
        return
 
    n = len(results["lengths"])
    click.echo()
    click.secho(f"Files scanned:     {results['files_scanned']}", bold=True)
    click.secho(f"Functions found:   {n}", bold=True)
    click.echo(f"Avg. length:            {sum(results['lengths']) / n:.2f} lines")
    click.echo(f"Avg. cyclomatic cplx:   {sum(results['complexities']) / n:.2f}")
    click.echo(f"Avg. nesting depth:     {sum(results['nestings']) / n:.2f}")
    click.echo(f"Total warnings:         {results['warnings']}")

#HELPERS--------------------------

#PRINTING STATS HELPERS

def countFilesAndDirs(directory):
    files=0
    dirs=0
    languages=[]
    for root,dir,file in os.walk(directory):
        dir[:] = [d for d in dir if d not in SKIP_DIRS]
        files+=len(file)
           
        dirs+=len(dir)
    
    click.echo(f"Total # Files:{files}")
    click.echo(f"Total # Directories:{dirs}")

def lang(directory):
    languages=[]
    for path,dirs,files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            ext=file.split('.')[-1]
            if ext in language_map:
                languages.append(language_map[ext])
    click.echo("Languages")
    click.echo("---------")
    printLang(languages=languages)

def printLang(languages):
    mapL={}
    for lang in languages:
        mapL[lang]=mapL.get(lang,0)+1
    for entry in mapL:
        click.echo(f"{entry}: {mapL[entry]} files")
def hasGit(directory:str)->bool:
    return (Path(directory)/".git").exists()

#Version 2
def countLangFiles(project):
    langDict={}
    maxFile=None
    maxLines=0
    filesCount=0
    for path,dirs,files in os.walk(project):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        # filesCount+=len(files)
        for file in files:
            ext=file.split('.')[-1]
            if ext in language_map:
                filesCount+=1
                full=os.path.join(path,file)
                numLines=countLines(full)
                if numLines>maxLines:
                    maxLines=numLines
                    maxFile=file

                langDict[ext]=langDict.get(ext,0)+numLines
    avg=0
    for key in langDict:
        if key in language_map:
            click.echo(f"{language_map[key]}: {langDict[key]} lines")
        avg+=langDict[key]
    click.echo("------------")
    click.echo(f"Largest File: {maxFile} ({maxLines} lines)")
    click.echo(f"Average File Size: {0 if filesCount==0  else avg//filesCount} lines")

def countLines(file):
    with open (file,"r",encoding="utf-8") as f:
        return sum(1 for line in f)
    

#Version 3
def gitRun(args, dir):
    #Runs git commands
    result = subprocess.run(["git"]+args,cwd=dir,capture_output=True,text=True)
    return result.stdout.strip()

#Version 4 Helpers
def folder_size(path):
    """Recursively sum the size (in bytes) of all files under path."""
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


                 

def emptyFiles(dir):
    total=0
    for root, dirs, files in os.walk(dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            path=os.path.join(root,file)
            if os.path.getsize(path)==0:
                total+=1
    return total

def dupFiles(dir):
    hMap={}
    count=0
    for root,dirs, files in os.walk(dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            if file in hMap:
                hMap[file]+=1
            else:
                hMap[file]=1
    
    for file, total in hMap.items():
        if total>1:
            count+=1
    # print(f"duplicates:{hMap.items()}")
    return count


#Version 6 Helpers
def fileCheck(dir):
    #README
    readMe=False
    license=False
    git=False
    env=False
    package=False
    for root, dirs, files in os.walk(dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        if "README.md" in files:
            readMe=True

        if "LICENSE" in files:
            license=True
        if ".gitignore" in files:
            git=True
        if ".env" in files:
            env=True
        if "package.json" in files:
            package=True

    if readMe:
        click.echo("README: Found")
    else:
        click.echo("README: Not Found")
    
    if license:
        click.echo("LICENSE: Found")
    else:
        click.echo("LICENSE: Not Found")
    
    if git:
        click.echo("Git Ignore: Found")
    else:
        click.echo("Git Ignore: Not Found")
    if env:
        click.echo(".env file: Found")
    else:
        click.echo(".env file: Not Found")
    if package:
        click.echo("Package JSON: Found")
    else:
        click.echo("Package JSON: Not Found")


def cyclomatic_complexity(func_node):
    """
    McCabe-style cyclomatic complexity: starts at 1, +1 per decision point
    (if/elif, for, while, except, boolean operators, comprehensions).
    """
    complexity = 1
    for node in ast.walk(func_node):
        if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try)):
            complexity += 1
        elif isinstance(node, ast.ExceptHandler):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            # "a and b and c" is 2 extra decision points, not 1
            complexity += len(node.values) - 1
        elif isinstance(node, (ast.comprehension,)):
            complexity += 1 + len(node.ifs)
    return complexity
 
 
def max_nesting_depth(node, current_depth=0):
    """Deepest level of nested control-flow blocks inside a function."""
    deepest = current_depth
    for child in ast.iter_child_nodes(node):
        # Don't descend into a nested function/class's own body for this metric
        if isinstance(child, FUNCTION_NODES + (ast.ClassDef,)) and child is not node:
            continue
        next_depth = current_depth + 1 if isinstance(child, NESTING_NODES) else current_depth
        deepest = max(deepest, max_nesting_depth(child, next_depth))
    return deepest
 
 
def function_length(func_node):
    """Line count spanned by the function, including its decorators."""
    start = min([func_node.lineno] + [d.lineno for d in func_node.decorator_list])
    end = getattr(func_node, "end_lineno", func_node.lineno)
    return end - start + 1
 
 
def count_warnings(filepath, source):
    """Run pyflakes against the source and count reported messages."""
    output = io.StringIO()
    reporter = Reporter(output, output)
    check(source, filepath, reporter)
    return len([line for line in output.getvalue().splitlines() if line.strip()])
 
 
def analyze_file(filepath, results):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, UnicodeDecodeError) as e:
        click.secho(f"  skipped {filepath}: {e}", fg="yellow")
        return
 
    for node in ast.walk(tree):
        if isinstance(node, FUNCTION_NODES):
            results["lengths"].append(function_length(node))
            results["complexities"].append(cyclomatic_complexity(node))
            results["nestings"].append(max_nesting_depth(node))
 
    results["warnings"] += count_warnings(filepath, source)
    results["files_scanned"] += 1
if __name__ == '__main__':
    cli()