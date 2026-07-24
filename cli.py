import click, os
from pathlib import Path
# Version 1
@click.command()
@click.option('-i','--directory',  type=click.Path(exists=True, file_okay=True,dir_okay=True),help='provides basic info on the directory')
@click.option("-s","--project", type=click.Path(exists=True, file_okay=True,dir_okay=True),help='provides basic info on the directory')
def cli(directory,project):
    if directory:
        printStats(directory)

    if project:
        sizeOf(project)


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

def sizeOf(project):
    click.echo("Lines of Code")
    click.echo("-------------")
    countLangFiles(project)


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

if __name__ == '__main__':
    cli()