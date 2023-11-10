
import os
import re
import http
import http.server
import urllib.parse
import socketserver
import webbrowser
import urllib
import dataclasses
import typing
import collections
import itertools

GRAPH_TEMPLATE = """digraph {{
/* Nodes */
{nodes}
/* Links */
{links}
/* Invisible Links (Used to pull nodes together without a visible link) */
{invis}
}}"""

ICONMAP = {
    "epic": "img/epic.png",
    "spike": "img/spike.png",
    "story": "img/story.png",
    "bug": "img/bug.png",
    "task": "img/task.png",
}


@dataclasses.dataclass()
class Issue:
    key: str
    summary: str
    links: typing.List["Link"] = dataclasses.field(default_factory=list)
    tags: typing.List[str] = dataclasses.field(default_factory=list)
    type: str = dataclasses.field(default="")


@dataclasses.dataclass()
class Link:
    name: str
    left: Issue
    right: Issue


def generateDotsGraph(issues: typing.Sequence[Issue]) -> str:
    nodes = {
        issue.key: (issue.key.replace("-", "_"), issue.summary.replace('"', r'\"'), ICONMAP.get(issue.type, "img/ball.png"))
        for issue in issues
    }
    node_string = "\n".join(f'{node}[label="{key}" title="{summary}" image="{icon}"]' for key, (node, summary, icon) in nodes.items())
    link_string = "\n".join(
        f'{nodes[link.left.key][0]} -> {nodes[link.right.key][0]}[title="{link.name}"]'
        for issue in issues
        for link in issue.links
    )
    tagMap = collections.defaultdict(set)
    for issue in issues:
        for tag in issue.tags:
            tagMap[tag].add(issue.key)
    tag_string = "\n".join(
        f'{nodes[left][0]} -- {nodes[right][0]}[title="{tag}" hidden="true" style="invis"]'
        for tag, keys in tagMap.items()
        for left, right in itertools.combinations(keys, 2)
    )

    return GRAPH_TEMPLATE.format(nodes=node_string, links=link_string, invis=tag_string)


class Handler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        directory = os.path.join(os.path.dirname(__file__), "www")
        super(Handler, self).__init__(*args, directory=directory, **kwargs)

    def do_GET(self):
        request = re.match(r"/api/(\w+)", self.path)
        if not request:
            super(Handler, self).do_GET()
            return

        if request.group(1) != "search":
            self.send_error(
                http.HTTPStatus.BAD_REQUEST,
                "Please use search endpoint",
            )
            return

        query = urllib.parse.urlparse(self.path).query
        parameters = urllib.parse.parse_qs(query)

        content = self.processQuery(parameters.get("search")).encode("utf8")

        self.send_response(http.HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain")
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def processQuery(self, query):
        if not query:
            return generateDotsGraph(())

        issues = [
            Issue(key="PROJ-123", summary="Amazing issue", tags=["blah"]),
            Issue(key="PROJ-456", summary="something else"),
            Issue(key="ITEM-789", summary="different project"),
            Issue(key="ITEM-111", summary="different project", type="task"),
            Issue(key="ITEM-432", summary="different project", type="task", tags=["blah"]),
            Issue(key="ITEM-212", summary="different project", type="bug", tags=["stuff"]),
            Issue(key="WORK-212", summary="doing work", type="story"),
            Issue(key="WORK-454", summary="doing more work", type="story", tags=["blah", "stuff"]),
        ]
        issues[0].links.append(Link("Relates to...", issues[0], issues[2]))
        issues[0].links.append(Link("Relates to...", issues[4], issues[5]))
        return generateDotsGraph(issues)


def main(netloc, port, search):
    with socketserver.TCPServer((netloc, port), Handler) as httpd:
        print("Running at port", port)
        query = urllib.parse.urlencode({"search": search})
        webbrowser.open(f"http://{netloc}:{port}?{query}")
        httpd.serve_forever()






if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", type=int, default=8090)
    parser.add_argument("-n", "--netloc", default="localhost")
    parser.add_argument("-s", "--search", default="")

    args = parser.parse_args()
    main(args.netloc, args.port, args.search)
