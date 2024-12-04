// External D3.js script (graph.js)

// Load JSON data
fetch("graph_data.json")
  .then(response => response.json())
  .then(graphData => {
    const svg = d3.select("svg");
    const width = +svg.attr("width");
    const height = +svg.attr("height");

    const subgraphColors = d3.scaleOrdinal(d3.schemePastel1);
    const subgraphs = Array.from(new Set(graphData.nodes.map(d => d.subgraph)));
    subgraphColors.domain(subgraphs);

    const degreeScale = d3.scaleLinear()
      .domain([1, d3.max(graphData.nodes, d =>
        graphData.links.filter(link => link.source === d.id || link.target === d.id).length)])
      .range([5, 20]);

    const simulation = d3.forceSimulation(graphData.nodes)
      .force("link", d3.forceLink(graphData.links).id(d => d.id).distance(50))
      .force("charge", d3.forceManyBody().strength(-100))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide().radius(d => degreeScale(d.degree) + 5));

    const link = svg.append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(graphData.links)
      .enter().append("line")
      .attr("class", "link");

    const node = svg.append("g")
      .attr("class", "nodes")
      .selectAll("circle")
      .data(graphData.nodes)
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

    simulation.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      node
        .attr("cx", d => d.x)
        .attr("cy", d => d.y);
    });

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
