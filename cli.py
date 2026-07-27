import click, os, subprocess, json, re
from pathlib import Path
# Version 1
@click.command()
@click.option('-i','--directory',  type=click.Path(exists=True, file_okay=True,dir_okay=True),help='provides basic info on the directory')
@click.option("-s","--project", type=click.Path(exists=True, file_okay=True,dir_okay=True),help='provides basic info on the size of files in directory')
@click.option("-g","--git", type=click.Path(exists=True, file_okay=True,dir_okay=True),help='provides git info on directory')
@click.option("-a","--dir", type=click.Path(exists=True, file_okay=True,dir_okay=True),help='provides git info on directory')
@click.option("-c","--stats", type=click.Path(exists=True, file_okay=True,dir_okay=True),help='provides additional info on directory')
@click.option("-h","--health", type=click.Path(exists=True, file_okay=True,dir_okay=True),help='provides health check on given directory')
def cli(directory,project,git,dir,stats,health):
    if directory:
        printStats(directory)

    if project:
        sizeOf(project)

    if git:
        gitInfo(git)
    if dir:
        analyzeDep(dir)
    if stats:
        codeStat(stats)

    if health:
        healthCheck(health)


#Version 1
def printStats(directory):
    click.echo(f"Project:{Path(directory).resolve().name}")
    click.echo(f"Root Directory:{os.path.abspath(directory)}")
    click.echo("")
    countFilesAndDirs(directory)
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
    click.echo(f"Modified:{modified.split("\n") if modified else []}")
    click.echo(f"Untracked:{untracked.split("\n") if untracked else []}")
    click.echo(f"Staged:{staged.split("\n") if staged else []}")

    click.echo()
    click.echo("Last Commit")
    click.echo("-----------")
    click.echo(f"Author: {commit['author']}")
    click.echo(f"Date: {commit['date']}")
    click.echo(f"Message: {commit['message']}")

#Version 4
#Starting with node first
def analyzeDep(dir):
    pkgPath=""
    for path,dirs,files in os.walk(dir):
        if "package.json" in files:
            pkgPath=os.path.join(path,"package.json")
            break
    
    if not pkgPath:
        raise Exception("No package.json found")
    with open(pkgPath,"r") as f:
        pkg=json.load(f)

    deps=pkg.get("dependencies",{})
    devDeps=pkg.get("devDependencies", {})
    click.echo("Dependencies")
    click.echo("------------")
    click.echo(f"Production: {len(deps)}")
    click.echo(f"Development: {len(devDeps)}")
    click.echo()
    click.echo("Largest Packages")
    click.echo("----------------")
    for i in sorted(deps.keys(), key=len, reverse=True)[:5]:
        click.echo(i)

#Version 5
def codeStat(dir):
    click.echo("Code Statistics")
    click.echo("---------------")
    click.echo(f"Print Statements: {printStat(dir)}")
    click.echo(f"Empty Files:{emptyFiles(dir)}")
    click.echo(f"Duplicate Files:{dupFiles(dir)}")

#Version 6
def healthCheck(dir):
    pass

#HELPERS--------------------------

#PRINTING STATS HELPERS

def countFilesAndDirs(directory):
    files=0
    dirs=0
    languages=[]
    for root,dir,file in os.walk(directory):
        files+=len(file)
           
        dirs+=len(dir)
    
    click.echo(f"Total # Files:{files}")
    click.echo(f"Total # Directories:{dirs}")

def lang(directory):
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
    languages=[]
    for path,dirs,files in os.walk(directory):
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
    maxFile=None
    maxLines=0
    filesCount=0
    for path,dirs,files in os.walk(project):
        filesCount+=len(files)
        for file in files:
            ext=file.split('.')[-1]
            if ext in language_map:
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
    click.echo(f"Average File Size: {avg//filesCount} lines")

def countLines(file):
    with open (file,"r",encoding="utf-8") as f:
        return sum(1 for line in f)
    

#Version 3
def gitRun(args, dir):
    #Runs git commands
    result = subprocess.run(["git"]+args,cwd=dir,capture_output=True,text=True)
    return result.stdout.strip()

#Version 5 Helpers
def printStat(dir):
     
    PRINT_PATTERNS = [
    r"console\.log\(",
    r"console\.error\(",
    r"console\.warn\(",
    r"console\.debug\(",
    r"\bprint\(",
    r"logging\.info\(",
    r"logging\.debug\(",
    r"logger\.info\(",
    r"logger\.debug\("
    ]
    total=0
    regex=re.compile("|".join(PRINT_PATTERNS))


    for root,dirs,files in os.walk(dir):
        for file in files:
            if file.endswith((".js",".py",".ts")):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        total += len(regex.findall(content))
                except:
                    pass
    return total
                 

def emptyFiles(dir):
    total=0
    for root, dirs, files in os.walk(dir):
        for file in files:
            path=os.path.join(root,file)
            if os.path.getsize(path)==0:
                total+=1
    return total

def dupFiles(dir):
    hMap={}
    count=0
    for root,dirs, files in os.walk(dir):
        for file in files:
            name=Path(file).stem
            if name in hMap:
                hMap[name]+=1
            else:
                hMap[name]=1
    
    for file, total in hMap.items():
        if total>1:
            count+=1
    
    return count


if __name__ == '__main__':
    cli()