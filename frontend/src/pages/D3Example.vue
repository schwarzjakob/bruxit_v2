<template>
    <svg id="chart" width="400" height="300"></svg>
</template>

<script setup>
import * as d3 from "d3";

 const data = [
      { x: 0, y: 5 },
      { x: 1, y: 9 },
    ];

    const svg = d3.select("#chart");
    const width = +svg.attr("width");
    const height = +svg.attr("height");

    // Define scales
    const xScale = d3.scaleLinear()
      .domain([0, d3.max(data, d => d.x)])
      .range([0, width]);

    const yScale = d3.scaleLinear()
      .domain([0, d3.max(data, d => d.y)])
      .range([height, 0]);

    // Define line generator
    const line = d3.line()
      .x(d => xScale(d.x))
      .y(d => yScale(d.y));

    // Append line to the SVG
    svg.append("path")
      .datum(data)
      .attr("fill", "none")
      .attr("stroke", "red")
      .attr("stroke-width", 8)
      .attr("d", line)
      .on("click", handleLineClick);

    function handleLineClick() {
      console.log("Line clicked!");
    }
</script>