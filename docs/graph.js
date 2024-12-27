fetch("graph_data.json")
  .then(response => response.json())
  .then(graphData => {
    const svg = d3.select("svg");
    const width = +svg.attr("width");
    const height = +svg.attr("height");

    const zoomGroup = svg.append("g");

    const subgraphColors = d3.scaleOrdinal(d3.schemePastel1);
    const subgraphs = Array.from(new Set(graphData.nodes.map(d => d.subgraph)));
    subgraphColors.domain(subgraphs);

    const centralNodes = subgraphs.map(subgraph => ({
      id: `central_${subgraph}`,
      subgraph: subgraph,
      isCentral: true,
      tooltip: subgraph
    }));

    const centralLinks = [];
    const interSubgraphConnections = new Set();

    // Identify subgraphs with links between them
    graphData.links.forEach(link => {
      const sourceNode = graphData.nodes.find(node => node.id === link.source);
      const targetNode = graphData.nodes.find(node => node.id === link.target);

      if (sourceNode && targetNode && sourceNode.subgraph !== targetNode.subgraph) {
        const subgraphPair = [sourceNode.subgraph, targetNode.subgraph].sort().join("-");
        interSubgraphConnections.add(subgraphPair);
      }
    });

    // Add central links based on inter-subgraph connections
    interSubgraphConnections.forEach(pair => {
      const [subgraphA, subgraphB] = pair.split("-");
      const centralA = centralNodes.find(node => node.subgraph === subgraphA);
      const centralB = centralNodes.find(node => node.subgraph === subgraphB);

      if (centralA && centralB) {
        centralLinks.push({
          source: centralA.id,
          target: centralB.id,
          isCentralLink: true
        });
      }
    });

    // Add links from central nodes to their subgraph nodes
    centralNodes.forEach(centralNode => {
      graphData.nodes.forEach(node => {
        if (node.subgraph === centralNode.subgraph && !node.isCentral) {
          centralLinks.push({
            source: centralNode.id,
            target: node.id,
            isCentralLink: false
          });
        }
      });
    });

    graphData.nodes = [...graphData.nodes, ...centralNodes];
    graphData.links = [...graphData.links, ...centralLinks];

    const degreeScale = d3.scaleLinear()
      .domain([1, d3.max(graphData.nodes, d =>
        graphData.links.filter(link => link.source === d.id || link.target === d.id).length)])
      .range([5, 20]);

    const simulation = d3.forceSimulation(graphData.nodes)
      .force("link", d3.forceLink(graphData.links)
        .id(d => d.id)
        .distance(d => {
          if (d.isCentralLink) return 300; // Longer distance for central-to-central links
          const sourceId = typeof d.source === "string" ? d.source : d.source.id;
          const targetId = typeof d.target === "string" ? d.target : d.target.id;

          const sourceSubgraph = typeof d.source === "string" ? graphData.nodes.find(n => n.id === d.source).subgraph : d.source.subgraph;
          const targetSubgraph = typeof d.target === "string" ? graphData.nodes.find(n => n.id === d.target).subgraph : d.target.subgraph;

          return sourceSubgraph === targetSubgraph ? 50 : 0;
        })
        .strength(d => {
          if (d.isCentralLink) return 0.1; // Weak force for central-to-central links
          const sourceSubgraph = typeof d.source === "string" ? graphData.nodes.find(n => n.id === d.source).subgraph : d.source.subgraph;
          const targetSubgraph = typeof d.target === "string" ? graphData.nodes.find(n => n.id === d.target).subgraph : d.target.subgraph;

          if (sourceSubgraph === targetSubgraph) return 0.5; // Strong force within subgraph
          return 0; // No force for inter-subgraph links
        }))
      .force("charge", d3.forceManyBody().strength(-100))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide().radius(d => degreeScale(d.degree) + 5));

    const link = zoomGroup.append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(graphData.links)
      .enter().append("line")
      .attr("stroke", d => (d.isCentralLink ? "none" : "gray"))
      .attr("stroke-width", 1.5);

    const node = zoomGroup.append("g")
      .attr("class", "nodes")
      .selectAll("circle")
      .data(graphData.nodes.filter(d => !d.isCentral))
      .enter().append("circle")
      .attr("r", d => {
        d.degree = graphData.links.filter(link => link.source === d.id || link.target === d.id).length;
        return degreeScale(d.degree);
      })
      .attr("fill", d => subgraphColors(d.subgraph))
      .on("click", (event, d) => {
        window.open(d.url, "_blank");
      })
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    node.append("title")
      .text(d => d.tooltip);

    const centralNodesText = zoomGroup.append("g")
      .attr("class", "central-nodes")
      .selectAll("text")
      .data(graphData.nodes.filter(d => d.isCentral))
      .enter().append("text")
      .text(d => d.tooltip)
      .attr("text-anchor", "middle")
      .attr("dy", "0.35em")
      .attr("font-size", "12px")
      .attr("font-weight", "bold")
      .style("fill", "black")
      .style("stroke", d => subgraphColors(d.subgraph))
      .style("stroke-width", "1px")
      .style("stroke-opacity", "1");

    simulation.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      node
        .attr("cx", d => d.x)
        .attr("cy", d => d.y);

      centralNodesText
        .attr("x", d => d.x)
        .attr("y", d => d.y);
    });

    const zoom = d3.zoom()
      .scaleExtent([0.5, 5])
      .on("zoom", (event) => {
        zoomGroup.attr("transform", event.transform);
      });

    svg.call(zoom);

    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }
  })
  .catch(error => console.error("Error loading graph data:", error));
