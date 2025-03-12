const svg = d3.select("svg"),
    width = +svg.attr("width"),
    height = +svg.attr("height")

let nodeData = []; // Stores current node data
let linkData = []; // Stores current link data
// let allNodes = {};  // Stores all nodes, key is id, value is node
let allLinks = [];  // Stores all links
// let allCentralNodes = {}; // Key is the subgraph, value is that subgraph's central node
// let allCentralLinks = {}; // Key is the subgraph, value is an array of the links to/from the central node
let subgraphNodeDict = {}; // Stores all nodes, key is the subgraph, value is an array of nodes belonging to that subgraph
let subgraphColors = d3.scaleOrdinal(d3.schemeTableau10);
let selectedSubgraphs = [];

// Create a container group that will be zoomed/panned
const container = svg.append("g");

// Separate groups for links and nodes
const linkGroup = container.append("g")
const nodeGroup = container.append("g")
    .attr("stroke", "#fff")
    .attr("stroke-width", 1.5);


// Initialize selections (empty for now)
let linkVisuals = linkGroup.selectAll(".link");
let nodeVisuals = nodeGroup.selectAll(".node");
let centralNodeVisuals = nodeGroup.selectAll(".central-node");
const centralNodeFontSize = 18;

// Add zoom and pan behavior to the container group
svg.call(
    d3.zoom()
      .scaleExtent([0.1, 20])
      .on("zoom", (event) => {
          container.attr("transform", event.transform);

      // Maintain constant size for central node text if zoomed out
      if (event.transform.k < 1) {
        centralNodeVisuals.style("font-size", `${centralNodeFontSize/event.transform.k}px`)
          .style("stroke-width", `${0.5 / event.transform.k}px`);
      }})
);

const simulation = d3.forceSimulation()
  .force("charge", d3.forceManyBody().strength(-100))
  .force("link", d3.forceLink().distance(100))
  .force("center", d3.forceCenter(width / 2, height / 2))
  .force("collide", d3.forceCollide().radius(d => nodeSize(d.degree) + 5))
  .force("x", d3.forceX(width / 2))
  .force("y", d3.forceY(height / 2))
  .on("tick", ticked);

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

loadGraphData();
// updateForces();
/**
 * Asynchronously loads graph data from external JSON files.
 * First attempts to load "simulation_position.json" for full position/transformation data.
 * If not found, falls back to "graph_data.json" which contains only node and link data.
 * Processes the loaded data to create subgraph checkboxes, records node and link information,
 * and create central nodes and their connections. Updates the global `allNodes`, `subgraphNodeDict`, 
 * and `allLinks` variables with the loaded data. 
 * Calls `updateGraphData` to refresh the visual representation of the graph.
 * Logs an error in the console if data loading fails.
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
    const graphData = await response.json();
    createSubgraphCheckboxes(graphData);

    // Record the node data
    graphData.nodes.forEach(node => {
      if (!subgraphNodeDict[node.subgraph]) {
        subgraphNodeDict[node.subgraph] = [];
      }
      subgraphNodeDict[node.subgraph].push(node)
    });

    // Record the link data
    graphData.links.forEach(link => {
      link.source = graphData.nodes.find(n => n.id === link.source) || link.source;
      link.target = graphData.nodes.find(n => n.id === link.target) || link.target;
      allLinks.push(link);
    });

    // Create central nodes if they don't exist
    let subgraphs = Array.from(new Set(graphData.nodes.map(d => d.subgraph)));
    subgraphs.forEach(subgraph => {
      centralNode = subgraphNodeDict[subgraph].find(node => node.isCentral);
      if (!centralNode) {
        centralNode = {
          id: `central_${subgraph}`,
          subgraph: subgraph,
          isCentral: true,
          tooltip: subgraph
        }
        subgraphNodeDict[subgraph].push(centralNode); // Add central node to subgraph nodes
      }
    })

    // Create links from central nodes to subgraph nodes
    subgraphs.forEach(subgraph => {
      const nodes = subgraphNodeDict[subgraph];
      const centralNode = nodes.find(node => node.isCentral);
      if (centralNode) {
        nodes.forEach(node => {
          if (!node.isCentral) {
            allLinks.push({ source: centralNode, target: node }); // Add link to allLinks
          }
        })
      }
    });

    // Set the domain of the color scale as the subgraphs
    subgraphColors.domain(subgraphs);

    updateGraphData();

  } catch (error) {
    console.error("Error loading graph data:", error);
    return null;
  }
}

/**
 * Updates the graph data to only include nodes and links present in the selected subgraphs.
 * Then restarts the graph simulation.
 * @return {undefined}
 */
function updateGraphData() {
  selectedSubgraphs = [];

  d3.selectAll("#checkbox-container input:checked").each(function () {
    selectedSubgraphs.push(this.value);
  });

  // Select only nodes present in the selected subgraphs
  nodeData = selectedSubgraphs.map(subgraph => subgraphNodeDict[subgraph]).flat().filter(Boolean);

  nodeIds = nodeData.map(d => d.id);

  // Create a map for fast node lookup
  let nodeMap = {};
  nodeData.forEach(node => {
    nodeMap[node.id] = node;
  });
  
  // Select only links present between selected nodes
  linkData = allLinks.filter(link => 
    nodeIds.includes(link.source.id) && 
    nodeIds.includes(link.target.id)
  ).map(link => {
    // Ensure links reference the actual node objects in the current simulation
    return {
      source: nodeMap[link.source.id],
      target: nodeMap[link.target.id]
    }
  });

  // Calculate degree for each node
  nodeData.forEach(node => {
    node.degree = linkData.filter(link => link.source.id === node.id).length + linkData.filter(link => link.target.id === node.id).length;
  })

  restart();
}

/**
 * Determines and updates the formatting and animation applied to the graph nodes and links.
 * @returns {undefined}
 */
function updateFormatting() {
  // Apply formatting to the non-central nodes
  nodeVisuals
    .attr("fill", d => subgraphColors(d.subgraph))
    .attr("r", d => nodeSize(d.degree))
    .attr("name", d => d.id)
    .call(d3.drag()                     // Add drag behavior
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended))

      // Add mouse events to show tooltips
      .on("mouseover", (event, d) => {
        nodeTooltip
          .style("opacity", 1) // Make the tooltip visible
          .html(`<strong>${d.tooltip}</strong>`); // Add tooltip content
        // Increase the node radius on hover
        d3.select(event.target)
          .transition().duration(200) // Smooth transition
          .attr("r", d => nodeSize(d.degree) * 1.3) // Increase radius
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
          .attr("r", d => nodeSize(d.degree)) // Reset radius
          .attr("stroke", "none"); // Remove outline
      })
      .on("click", (event, d) => {
        // Open the url in a new tab
        window.open(d.url, "_blank");
      });

  // Apply formatting to the central nodes
  centralNodeVisuals
    .text(d => d.tooltip)
    .attr("text-anchor", "middle")
    .attr("dy", "0.35em")
    .attr("font-size", `${centralNodeFontSize}px`)
    .attr("font-weight", "900")
    .style("fill", d => subgraphColors(d.subgraph))
    .style("stroke", "white")
    .style("stroke-width", "0.5px")
    .style("stroke-opacity", "1")
    .call(d3.drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended));

  // Apply formatting to the non-central links
  linkVisuals.filter(d => !d.source.isCentral && !d.target.isCentral)
    .attr("stroke", d => {
      if (d.source.subgraph === d.target.subgraph) {
        return "blue";
      } else {
        return subgraphColors(d.source.subgraph);
      }
    })
    .attr("stroke-opacity", 0.5)
    .attr("stroke-width", 1.5)
    .attr("stroke-dasharray", d => d.source.subgraph !== d.target.subgraph ? "4,2" : "")

    // Add mouse events to show tooltips
    .on("mouseover", (event, d) => {
      linkTooltip
        .style("opacity", 1) // Make the tooltip visible
        .html(`<strong>${d.source.id + " ->\n" + d.target.id}</strong>`); // Add tooltip content

      d3.select(event.target)
        .transition().duration(200)
        .attr("stroke", "black") // Add black outline
        .attr("stroke-width", 2); // increase outline width
    })
    .on("mousemove", (event) => {
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


  // Apply formatting to the central links
  linkVisuals.filter(d => d.source.isCentral || d.target.isCentral)
    .attr("stroke-opacity", 0)
}


/**
 * Calculates and updates the forces applied to the simulation.
 * @returns {undefined}
 */
function updateForces() {
  subgraphCount = selectedSubgraphs.length;

  simulation.force("link") // Select the EXISTING link force
      .distance(link => {     // Update its distance function
          const sourceSubgraph = link.source.subgraph;
          const targetSubgraph = link.target.subgraph;
          if (sourceSubgraph === targetSubgraph) {
              return 5;
          } else {
              return Math.sqrt(subgraphCount) * 5 + 15;
          }
      })
      .strength(link => {     // Update its strength function
          const sourceSubgraph = link.source.subgraph;
          const targetSubgraph = link.target.subgraph;
          if (sourceSubgraph === targetSubgraph) {
              return 0.5;
          } else {
              return 2/subgraphCount**2
          }
      });

  simulation.force("charge") // Select the EXISTING charge force
      .strength(d => {        // Update its strength function
          return -900 / subgraphCount;
      });


}

/**
 * Restarts the simulation and updates the visual representation of the graph to reflect the new data.
 * @returns {undefined}
 */
function restart() {
  // Bind the data to the node visuals in the DOM
  nodeVisuals = nodeGroup.selectAll(".node").data(nodeData.filter(d => !d.isCentral), d => d.id);
  // Remove any nodes that are no longer in the data (exited nodes)
  nodeVisuals.exit().remove();
  // Add any new nodes that are in the data (entered nodes)
  nodeVisuals = nodeVisuals.enter().append("circle")
    .attr("class", "node")
    .merge(nodeVisuals); // Combines the entered nodes with the existing nodes into the DOM visuals

  // Bind the data to the central node visuals in the DOM
  centralNodeVisuals = nodeGroup.selectAll(".central-node").data(nodeData.filter(d => d.isCentral), d => d.id);
  // Remove any central nodes that are no longer in the data (exited central nodes)
  centralNodeVisuals.exit().remove();
  // Add any new central nodes that are in the data (entered central nodes)
  centralNodeVisuals = centralNodeVisuals.enter().append("text")
    .attr("class", "central-node")
    .merge(centralNodeVisuals);

  // Update links
  linkVisuals = linkVisuals.data(linkData, d => d.source.id + "-" + d.target.id);
  linkVisuals.exit().remove();
  linkVisuals = linkVisuals.enter()
    .append("line")
    .attr("class", "link")
    .merge(linkVisuals);

  // Update simulation with new nodes and links
  simulation.nodes(nodeData);
  simulation.force("link").links(linkData);

  console.log(simulation.force("link"));

  updateFormatting();
  updateForces();

  // Restart the simulation
  simulation.alpha(0.3).restart();
  
}

/**
 * The callback for the 'tick' simulation event. 
 * 
 * Updates the visual positions of the nodes and links based on the current positions 
 * of the nodes in the simulation. 
 */
function ticked() {
    nodeVisuals.attr("cx", d => d.x)
        .attr("cy", d => d.y);

    centralNodeVisuals.attr("x", d => d.x)
        .attr("y", d => d.y);

    linkVisuals.attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);
}

function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.1).restart();
    d.fx = d.x;
    d.fy = d.y;

    if (d.isCentral) return; // Don't show tooltip for central nodes
    // Make tooltip visible and set initial position on drag start
    nodeTooltip.style("opacity", 1)
      .style("left", `${event.sourceEvent.pageX + 10}px`)  // Use event.x
      .style("top", `${event.sourceEvent.pageY + 10}px`)   // Use event.y
      .html(`<strong>${d.tooltip}</strong>`);
}

function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;

    if (d.isCentral) return;
    // Update tooltip position during drag
    nodeTooltip
      .style("left", `${event.sourceEvent.pageX + 10}px`)  // Use event.x
      .style("top", `${event.sourceEvent.pageY + 10}px`);   // Use event.y
}

function dragended(event, d) {
  if (!event.active) simulation.alphaTarget(0);
  d.fx = null;
  d.fy = null;
  // Hide tooltip on drag end
  // nodeTooltip.style("opacity", 0);
  // console.log("Tooltip style in dragended:", nodeTooltip.style("opacity"), nodeTooltip.style("left"), nodeTooltip.style("top")); // Log tooltip style
}

 // New drag behavior for central nodes (dragging the text)
function draggedCentral(event, d) {
  d.fx = event.x;
  d.fy = event.y;
}

function nodeSize(degree) {
  return 2 + degree ** 0.7;
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
            .attr("value", subgraph)
            .on("change", function () {
                updateGraphData();
            });

        label.append("label")
            .attr("class", "form-check-label")
            .attr("for", `checkbox-${subgraph}`)
            .text(subgraph);
    });
}