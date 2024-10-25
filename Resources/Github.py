import aiohttp

async def fetch_latest_commit(repo_owner, repo_name, branch):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits?sha={branch}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data:
                    latest_commit = data[0]
                    commit_message = latest_commit['commit']['message']
                    commit_url = latest_commit['html_url']
                    commit_author = latest_commit['commit']['author']['name']
                    commit_date = latest_commit['commit']['author']['date']
                    commit_hash = latest_commit['sha'][:7]
                    return {
                        "message": commit_message,
                        "url": commit_url,
                        "author": commit_author,
                        "date": commit_date,
                        "short_hash": commit_hash
                    }
                else:
                    return None
            else:
                print(f"Failed to fetch the latest commit: {response.status}")
                return None
