# This scr1pt will create a new project
# It will create the meta data of the project, such as unique project key, git repo, artifact name.

# read @args
while getopts ":p:g:a:" opt; do
  case $opt in
    p)
      project_name="$OPTARG"
      ;;
    g)
      git_repo="$OPTARG"
      ;;
    a)
      artifact_name="$OPTARG"
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done

# init project by args
