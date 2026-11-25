# Repository wiki with OpenWiki

Start with the [OpenWiki quickstart](../openwiki/quickstart.md). It links the canonical model, analysis, risk reports, imports and workflow checks to their source and tests. The [documentation hub](README.md) contains the detailed user guides.

## Local integration

OpenWiki 0.7.2 requires Node.js 22.22.0 or newer. Install the pinned CLI to maintain the wiki through an agent integration.

```sh
npm install --global openwiki@0.7.2
```

Choose a host in the [upstream quick start](https://github.com/langchain-ai/openwiki#quick-start) and add `--project .` to its integration install command from the repository root. Reopen the repository in that host to load the integration.

## Maintenance

Use the [repository brief](../openwiki/INSTRUCTIONS.md) and [source exclusions](../.openwikiignore) when updating the wiki. Keep pages about the published package aligned with the corresponding release. Review claims against their sources and check that updated sections can be found and read.
