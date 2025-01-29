// let globalTransform = { x: 0, y: 0 , k: -1 };

/* 
This function looks for simulation_position.json in the current directory, if it is not found, graph_data.json is used.
simulation_position.json is created by the download button at the bottom of the page and has full position/transformation data.
graph_data.json is the original data used to create the graph. It has no positioning/transformation data, just the node and link data.
*/
async function loadGraphData() {
  try {
    const response = await fetch("simulation_position.json");
    if (!response.ok) {
      response = await fetch("graph_data.json");
      if (!response.ok) {
        throw new Error("Failed to fetch graph data");
      }
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error loading graph data:", error);
    return null;
  }
}

let graphData = await loadGraphData();

let simulation;
// let globalTransform = { x: 0, y: 0 , k: -1 };

fetch("graph_data.json")
  .then(response => response.json())
  .then(graphData => {
    const fullGraphData = graphData;
    let currentGraphData = fullGraphData;

    createSubgraphCheckboxes(fullGraphData); // Generate the subgraph checkboxes to the left of the svg

    var subgraphColors = d3.scaleOrdinal(d3.schemeTableau10);
    const fullSubgraphs = Array.from(new Set(graphData.nodes.map(d => d.subgraph)));
    subgraphColors.domain(fullSubgraphs);

    visualizeGraph(graphData);

    function visualizeGraph(graphData) {
      const svg = d3.select("svg");
      svg.selectAll("*").remove(); // Clear the SVG
      const width = +svg.attr("width");
      const height = +svg.attr("height");

      let subgraphs = Array.from(new Set(graphData.nodes.map(d => d.subgraph)));

      const zoomGroup = svg.append("g");
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

      // Precompute node degrees
      graphData.nodes.forEach(node => {
        node.degree = graphData.links.filter(
          link => link.source === node.id || link.target === node.id
        ).length;
      });

      // Update degreeScale to use the precomputed degrees
      const degreeScale = d3.scaleLinear()
        .domain([1, d3.max(graphData.nodes, d => d.degree)]) // Use precomputed degrees
        .range([5, 20]);
      console.log(subgraphs.length);

      simulation = d3.forceSimulation(graphData.nodes)
        .force("link", d3.forceLink(graphData.links)
          .id(d => d.id)
          .distance(d => {
            if (d.isCentralLink) return subgraphs.length * 10; // Longer distance for central-to-central links that increases as the number of subgraphs increase
            const sourceId = typeof d.source === "string" ? d.source : d.source.id;
            const targetId = typeof d.target === "string" ? d.target : d.target.id;

            const sourceSubgraph = typeof d.source === "string" ? graphData.nodes.find(n => n.id === d.source).subgraph : d.source.subgraph;
            const targetSubgraph = typeof d.target === "string" ? graphData.nodes.find(n => n.id === d.target).subgraph : d.target.subgraph;

            return sourceSubgraph === targetSubgraph ? 50 : 0;
          })
          .strength(d => {
            if (d.isCentralLink) return 8/subgraphs.length**2; // Weak force for central-to-central links that decrease as the number of subgraphs increase
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
        .attr("stroke", d => {
          const sourceId = typeof d.source === "string" ? d.source : d.source.id;
          if (sourceId.startsWith("central_")) {
            return "none";
          }
          if (d.source.subgraph !== d.target.subgraph) {
            return subgraphColors(d.source.subgraph);
          }
          return "blue";
        })
        .attr("stroke-width", 1.5)
        .attr("stroke-dasharray", d => d.source.subgraph !== d.target.subgraph ? "4,2" : "");

      // link.append("title")
      //   .text(d => d.source.id + " ->\n" + d.target.id);


      // Create a tooltip element (if not already created)
      const linkTooltip = d3.select("body").append("div")
        .attr("class", "custom-tooltip")
        .style("position", "absolute")
        .style("pointer-events", "none") // Prevent tooltip from interfering with mouse events
        .style("background", "#fff")
        .style("border", "1px solid #ccc")
        .style("border-radius", "4px")
        .style("padding", "8px")
        .style("box-shadow", "0 2px 5px rgba(0, 0, 0, 0.2)")
        .style("opacity", 0); // Initially hidden

      // Add mouse events to show tooltips
      link.on("mouseover", (event, d) => {
        linkTooltip
          .style("opacity", 1) // Make the tooltip visible
          .html(`<strong>${d.source.id + " ->\n" + d.target.id}</strong>`); // Add tooltip content

        d3.select(event.target)
          .transition().duration(200)
          .attr("stroke", "black") // Add black outline
          .attr("stroke-width", 2); // increase outline width
      })
      link.on("mousemove", (event) => {
        linkTooltip
          .style("left", `${event.pageX + 10}px`) // Offset the tooltip to the right of the cursor
          .style("top", `${event.pageY + 10}px`); // Offset the tooltip slightly below the cursor
      })
      .on("mouseout", (event) => {
        linkTooltip
          .style("opacity", 0); // Hide the tooltip

        d3.select(event.target)
          .transition().duration(200)
          .attr("stroke", d => {
            const sourceId = typeof d.source === "string" ? d.source : d.source.id;
            if (sourceId.startsWith("central_")) {
              return "none";
            }
            if (d.source.subgraph !== d.target.subgraph) {
              return subgraphColors(d.source.subgraph);
            }
            return "blue";
          })
          .attr("stroke-width", 1.5);
      });

    // Adjust the node rendering to use precomputed degree
    const node = zoomGroup.append("g")
      .attr("class", "nodes")
      .selectAll("circle")
      .data(graphData.nodes.filter(d => !d.isCentral))
      .enter().append("circle")
      .attr("r", d => degreeScale(d.degree)) // Use degreeScale with precomputed degree
      .attr("fill", d => subgraphColors(d.subgraph))
      .on("click", (event, d) => {
        window.open(d.url, "_blank");
      })
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

        // node.append("title")
        //   .text(d => d.tooltip);

      // Create a tooltip element (if not already created)
      const nodeTooltip = d3.select("body").append("div")
        .attr("class", "custom-tooltip")
        .style("position", "absolute")
        .style("pointer-events", "none") // Prevent tooltip from interfering with mouse events
        .style("background", "#fff")
        .style("border", "1px solid #ccc")
        .style("border-radius", "4px")
        .style("padding", "8px")
        .style("box-shadow", "0 2px 5px rgba(0, 0, 0, 0.2)")
        .style("opacity", 0); // Initially hidden

      // Add mouse events to show tooltips
      node.on("mouseover", (event, d) => {
        nodeTooltip
          .style("opacity", 1) // Make the tooltip visible
          .html(`<strong>${d.tooltip}</strong>`); // Add tooltip content
        // Increase the node radius on hover
        d3.select(event.target)
          .transition().duration(200) // Smooth transition
          .attr("r", d => degreeScale(d.degree) * 1.3) // Increase radius
          .attr("stroke", "black") // Add black outline
          .attr("stroke-width", 2); // Set outline width
      })
      .on("mousemove", (event) => {
        nodeTooltip
          .style("left", `${event.pageX + 10}px`) // Offset the tooltip to the right of the cursor
          .style("top", `${event.pageY + 10}px`); // Offset the tooltip slightly below the cursor
      })
      .on("mouseout", (event) => {
        nodeTooltip
          .style("opacity", 0); // Hide the tooltip
        // Reset the node radius on mouseout
        d3.select(event.target)
          .transition().duration(200) // Smooth transition
          .attr("r", d => degreeScale(d.degree)) // Reset radius
          .attr("stroke", "none"); // Remove outline
      });

      // Add text labels for central nodes
      const centralNodesText = zoomGroup.append("g")
        .attr("class", "central-nodes")
        .selectAll("text")
        .data(graphData.nodes.filter(d => d.isCentral))
        .enter().append("text")
        .text(d => d.tooltip)
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em")
        .attr("font-size", "14px")
        .attr("font-weight", "900")
        .style("fill", d => subgraphColors(d.subgraph))
        .style("stroke", "white")
        .style("stroke-width", "0.5px")
        .style("stroke-opacity", "1")
        .call(d3.drag()
          .on("start", dragstarted)
          .on("drag", draggedCentral)
          .on("end", dragended));

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
        .scaleExtent([0.2, 10])
        .on("zoom", (event) => {
          zoomGroup.attr("transform", event.transform);

          // Maintain constant size for central node text if zoomed out
          if (event.transform.k < 1) {
            centralNodesText.style("font-size", `${14 / (event.transform.k)}px`)
              .style("stroke-width", `${0.5 / event.transform.k}px`);
          }
        });

      svg.call(zoom);



    }
    
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

    // New drag behavior for central nodes (dragging the text)
    function draggedCentral(event, d) {
      d.fx = event.x;
      d.fy = event.y;
      d3.select(this)
        .attr("x", event.x)
        .attr("y", event.y);
    }

    
    // Generate checkboxes dynamically based on subgraphs
    function createSubgraphCheckboxes(graphData) {
        // Extract unique subgraph names
        const subgraphs = Array.from(new Set(graphData.nodes.map(node => node.subgraph)));

        // Select the checkbox container
        const checkboxContainer = d3.select("#checkbox-container");

        // Add a title
        checkboxContainer.append("p").text("Subgraph Filters:");

        // Add a checkbox for each subgraph
        subgraphs.forEach(subgraph => {
            const label = checkboxContainer.append("div").attr("class", "form-check");

            label.append("input")
                .attr("type", "checkbox")
                .attr("class", "form-check-input")
                .attr("id", `checkbox-${subgraph}`)
                .attr("checked", true)
                .on("change", function () {
                    toggleSubgraph(subgraph, this.checked);
                });

            label.append("label")
                .attr("class", "form-check-label")
                .attr("for", `checkbox-${subgraph}`)
                .text(subgraph);
        });
    }
    function removeSubgraph(subgraph) {
        const gDnodesRemoved = simulation.nodes().filter(node => !(node.subgraph === subgraph || node.isCentral));
        const gDlinksRemoved = simulation.force("link").links().filter(link => link.source.subgraph !== subgraph && link.target.subgraph !== subgraph);
        const graphData = { nodes: gDnodesRemoved, links: gDlinksRemoved };
        visualizeGraph(graphData);
    }

    // Handle checkbox toggling
    function toggleSubgraph(subgraph, isChecked) {
        if (isChecked) {
            console.log(`Show subgraph: ${subgraph}`);
            // Add your logic to re-add the subgraph
        } else {
            console.log(`Remove subgraph: ${subgraph}`);
            removeSubgraph(subgraph);
        }
    }
  })
  .catch(error => console.error("Error loading graph data:", error));

let graphData = await loadGraphData();
const fullGraphData = graphData;
function initializeGraph() {


    const inititalNodeData = simulationData.nodes;
    const initialLinkData = simulationData.links;
    const initialTransform =  d3.zoomIdentity.translate(translateX, translateY).scale(scale);
    let currentGraphData = fullGraphData;

    createSubgraphCheckboxes(fullGraphData); // Generate the subgraph checkboxes to the left of the svg

    var subgraphColors = d3.scaleOrdinal(d3.schemeTableau10);
    const fullSubgraphs = Array.from(new Set(graphData.nodes.map(d => d.subgraph)));
    subgraphColors.domain(fullSubgraphs);

    visualizeGraph(graphData);

    function visualizeGraph(graphData) {
      const svg = d3.select("svg");
      svg.selectAll("*").remove(); // Clear the SVG
      const width = +svg.attr("width");
      const height = +svg.attr("height");

      let subgraphs = Array.from(new Set(graphData.nodes.map(d => d.subgraph)));

      const zoomGroup = svg.append("g");
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

      // Precompute node degrees
      graphData.nodes.forEach(node => {
        node.degree = graphData.links.filter(
          link => link.source === node.id || link.target === node.id
        ).length;
      });

      // Update degreeScale to use the precomputed degrees
      const degreeScale = d3.scaleLinear()
        .domain([1, d3.max(graphData.nodes, d => d.degree)]) // Use precomputed degrees
        .range([5, 20]);
      console.log(subgraphs.length);

      simulation = d3.forceSimulation(graphData.nodes)
        .force("link", d3.forceLink(graphData.links)
          .id(d => d.id)
          .distance(d => {
            if (d.isCentralLink) return subgraphs.length * 10; // Longer distance for central-to-central links that increases as the number of subgraphs increase
            const sourceId = typeof d.source === "string" ? d.source : d.source.id;
            const targetId = typeof d.target === "string" ? d.target : d.target.id;

            const sourceSubgraph = typeof d.source === "string" ? graphData.nodes.find(n => n.id === d.source).subgraph : d.source.subgraph;
            const targetSubgraph = typeof d.target === "string" ? graphData.nodes.find(n => n.id === d.target).subgraph : d.target.subgraph;

            return sourceSubgraph === targetSubgraph ? 50 : 0;
          })
          .strength(d => {
            if (d.isCentralLink) return 8/subgraphs.length**2; // Weak force for central-to-central links that decrease as the number of subgraphs increase
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
        .attr("stroke", d => {
          const sourceId = typeof d.source === "string" ? d.source : d.source.id;
          if (sourceId.startsWith("central_")) {
            return "none";
          }
          if (d.source.subgraph !== d.target.subgraph) {
            return subgraphColors(d.source.subgraph);
          }
          return "blue";
        })
        .attr("stroke-width", 1.5)
        .attr("stroke-dasharray", d => d.source.subgraph !== d.target.subgraph ? "4,2" : "");

      // link.append("title")
      //   .text(d => d.source.id + " ->\n" + d.target.id);


      // Create a tooltip element (if not already created)
      const linkTooltip = d3.select("body").append("div")
        .attr("class", "custom-tooltip")
        .style("position", "absolute")
        .style("pointer-events", "none") // Prevent tooltip from interfering with mouse events
        .style("background", "#fff")
        .style("border", "1px solid #ccc")
        .style("border-radius", "4px")
        .style("padding", "8px")
        .style("box-shadow", "0 2px 5px rgba(0, 0, 0, 0.2)")
        .style("opacity", 0); // Initially hidden

      // Add mouse events to show tooltips
      link.on("mouseover", (event, d) => {
        linkTooltip
          .style("opacity", 1) // Make the tooltip visible
          .html(`<strong>${d.source.id + " ->\n" + d.target.id}</strong>`); // Add tooltip content

        d3.select(event.target)
          .transition().duration(200)
          .attr("stroke", "black") // Add black outline
          .attr("stroke-width", 2); // increase outline width
      })
      link.on("mousemove", (event) => {
        linkTooltip
          .style("left", `${event.pageX + 10}px`) // Offset the tooltip to the right of the cursor
          .style("top", `${event.pageY + 10}px`); // Offset the tooltip slightly below the cursor
      })
      .on("mouseout", (event) => {
        linkTooltip
          .style("opacity", 0); // Hide the tooltip

        d3.select(event.target)
          .transition().duration(200)
          .attr("stroke", d => {
            const sourceId = typeof d.source === "string" ? d.source : d.source.id;
            if (sourceId.startsWith("central_")) {
              return "none";
            }
            if (d.source.subgraph !== d.target.subgraph) {
              return subgraphColors(d.source.subgraph);
            }
            return "blue";
          })
          .attr("stroke-width", 1.5);
      });

    // Adjust the node rendering to use precomputed degree
    const node = zoomGroup.append("g")
      .attr("class", "nodes")
      .selectAll("circle")
      .data(graphData.nodes.filter(d => !d.isCentral))
      .enter().append("circle")
      .attr("r", d => degreeScale(d.degree)) // Use degreeScale with precomputed degree
      .attr("fill", d => subgraphColors(d.subgraph))
      .on("click", (event, d) => {
        window.open(d.url, "_blank");
      })
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

        // node.append("title")
        //   .text(d => d.tooltip);

      // Create a tooltip element (if not already created)
      const nodeTooltip = d3.select("body").append("div")
        .attr("class", "custom-tooltip")
        .style("position", "absolute")
        .style("pointer-events", "none") // Prevent tooltip from interfering with mouse events
        .style("background", "#fff")
        .style("border", "1px solid #ccc")
        .style("border-radius", "4px")
        .style("padding", "8px")
        .style("box-shadow", "0 2px 5px rgba(0, 0, 0, 0.2)")
        .style("opacity", 0); // Initially hidden

      // Add mouse events to show tooltips
      node.on("mouseover", (event, d) => {
        nodeTooltip
          .style("opacity", 1) // Make the tooltip visible
          .html(`<strong>${d.tooltip}</strong>`); // Add tooltip content
        // Increase the node radius on hover
        d3.select(event.target)
          .transition().duration(200) // Smooth transition
          .attr("r", d => degreeScale(d.degree) * 1.3) // Increase radius
          .attr("stroke", "black") // Add black outline
          .attr("stroke-width", 2); // Set outline width
      })
      .on("mousemove", (event) => {
        nodeTooltip
          .style("left", `${event.pageX + 10}px`) // Offset the tooltip to the right of the cursor
          .style("top", `${event.pageY + 10}px`); // Offset the tooltip slightly below the cursor
      })
      .on("mouseout", (event) => {
        nodeTooltip
          .style("opacity", 0); // Hide the tooltip
        // Reset the node radius on mouseout
        d3.select(event.target)
          .transition().duration(200) // Smooth transition
          .attr("r", d => degreeScale(d.degree)) // Reset radius
          .attr("stroke", "none"); // Remove outline
      });

      // Add text labels for central nodes
      const centralNodesText = zoomGroup.append("g")
        .attr("class", "central-nodes")
        .selectAll("text")
        .data(graphData.nodes.filter(d => d.isCentral))
        .enter().append("text")
        .text(d => d.tooltip)
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em")
        .attr("font-size", "14px")
        .attr("font-weight", "900")
        .style("fill", d => subgraphColors(d.subgraph))
        .style("stroke", "white")
        .style("stroke-width", "0.5px")
        .style("stroke-opacity", "1")
        .call(d3.drag()
          .on("start", dragstarted)
          .on("drag", draggedCentral)
          .on("end", dragended));

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
        .scaleExtent([0.2, 10])
        .on("zoom", (event) => {
          zoomGroup.attr("transform", event.transform);

          // Maintain constant size for central node text if zoomed out
          if (event.transform.k < 1) {
            centralNodesText.style("font-size", `${14 / (event.transform.k)}px`)
              .style("stroke-width", `${0.5 / event.transform.k}px`);
          }
        });

      svg.call(zoom);
      
      scale = 0.5
      translateX = width / 2 * (1 - scale)
      translateY = height / 2 * (1 - scale)
      const initialTransform = d3.zoomIdentity.translate(translateX, translateY).scale(scale); // Define initial transform
      // Apply the zoom behavior to the svg
      svg.call(d3.zoom()
          .on("zoom", (event) => {
              zoomGroup.attr("transform", event.transform);
          }))
          .call(zoom.transform, initialTransform); // Set the initial zoom level

    }
    
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

    // New drag behavior for central nodes (dragging the text)
    function draggedCentral(event, d) {
      d.fx = event.x;
      d.fy = event.y;
      d3.select(this)
        .attr("x", event.x)
        .attr("y", event.y);
    }

    
    // Generate checkboxes dynamically based on subgraphs
    function createSubgraphCheckboxes(graphData) {
        // Extract unique subgraph names
        const subgraphs = Array.from(new Set(graphData.nodes.map(node => node.subgraph)));

        // Select the checkbox container
        const checkboxContainer = d3.select("#checkbox-container");

        // Add a title
        checkboxContainer.append("p").text("Subgraph Filters:");

        // Add a checkbox for each subgraph
        subgraphs.forEach(subgraph => {
            const label = checkboxContainer.append("div").attr("class", "form-check");

            label.append("input")
                .attr("type", "checkbox")
                .attr("class", "form-check-input")
                .attr("id", `checkbox-${subgraph}`)
                .attr("checked", true)
                .on("change", function () {
                    toggleSubgraph(subgraph, this.checked);
                });

            label.append("label")
                .attr("class", "form-check-label")
                .attr("for", `checkbox-${subgraph}`)
                .text(subgraph);
        });
    }
    function removeSubgraph(subgraph) {
        const gDnodesRemoved = simulation.nodes().filter(node => !(node.subgraph === subgraph || node.isCentral));
        const gDlinksRemoved = simulation.force("link").links().filter(link => link.source.subgraph !== subgraph && link.target.subgraph !== subgraph);
        const graphData = { nodes: gDnodesRemoved, links: gDlinksRemoved };
        visualizeGraph(graphData);
    }

    // Handle checkbox toggling
    function toggleSubgraph(subgraph, isChecked) {
        if (isChecked) {
            console.log(`Show subgraph: ${subgraph}`);
            // Add your logic to re-add the subgraph
        } else {
            console.log(`Remove subgraph: ${subgraph}`);
            removeSubgraph(subgraph);
        }
    }
  })
  .catch(error => console.error("Error loading graph data:", error));


// Assuming the simulation and zoom setup are already created

// Create the button
const button = document.createElement("button");
button.textContent = "Download Simulation Position";
button.style.display = "block";
button.style.margin = "10px auto";
button.style.padding = "10px";
button.style.cursor = "pointer";

// Add the button below the SVG
document.body.appendChild(button);

// Function to download JSON data
function downloadJSON(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// Attach click event to the button
button.addEventListener("click", () => {
    // Retrieve the current zoom/pan transformation
    const transform = d3.zoomTransform(d3.select("svg").node());
    
    // Prepare the data to download
    const simulationData = {
        nodes: simulation.nodes(), // Nodes array from the simulation
        links: simulation.force("link").links(), // Links array from the simulation
        transformation: {
            translateX: transform.x,
            translateY: transform.y,
            scale: transform.k
        }
    };

    // Download the JSON file
    downloadJSON(simulationData, "simulation_position.json");
});
