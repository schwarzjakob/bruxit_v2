<template>
    <div>
      <!-- Chart container -->
      <div v-if="!chartInitialized">Loading chart...</div>
      <el-button id="add-event-button">+ Add event</el-button>
      <div id="myChart" style="width: 100%; height: 400px;"></div>
      <!-- Loading indicator -->
      <div v-if="startSelection && endSelection"> Start: {{ startSelection }} s, End: {{ endSelection }} s , Duration: {{ duration }} s</div>
    </div>
  </template>
  
  <script>
  import * as echarts from 'echarts';
  import csv from '../assets/0204451eFnorm_MR_5_min_resampled.csv'; // Adjust the path as needed
  
  export default {
    name: 'LineChart',
    data() {
      return {
        MR: [],                // This will store the cleaned values from the 'MR' column
        timeAxis: [],          // This will store the time values for the x-axis
        chartInitialized: false,  // Track when the chart has been initialized
        startSelection: null,
        endSelection: null,
        duration: null
      };
    },
    async mounted() {
      await this.processDataAndInitializeChart(); // Wait for data processing before initializing the chart
    },
    methods: {   
        handleBrushSelection(params) {
            const selected = params.batch[0];
            if (selected) {
                const { areas } = selected;
                
                if (areas.length === 0){
                    this.startSelection = null;
                    this.endSelection = null;
                    this.duration = null;
                } else {
                    areas.forEach(area => {
                    const { brushType, coordRange } = area;
                    //const { xAxisIndex, yAxisIndex } = area;
                    const [startCoord, endCoord] = coordRange;

                    console.log(`Brush type: ${brushType}`);
                    console.log(`Start coordinate: ${startCoord}`);
                    console.log(`End coordinate: ${endCoord}`);
                    this.startSelection = (startCoord/500).toFixed(2);
                    this.endSelection = (endCoord/500).toFixed(2);
                    this.duration = (this.endSelection - this.startSelection).toFixed(2);
                    });
                }
            }
        },
        async processDataAndInitializeChart() {
            try {
            // Log the CSV data to debug its structure
            //console.log("CSV Data:", csv);
    
            // Assume the first row is the header
            const header = csv[0];
            const mrIndex = header.indexOf('MR'); // Find the index of the 'MR' column
    
            if (mrIndex === -1) {
                throw new Error('Column "MR" not found in header');
            }
    
            // Remove any empty rows and validate data
            const filteredRows = csv.slice(1).filter(row => row.length > 1);
    
            // Extract and clean the 'MR' column from the filtered data
            this.MR = filteredRows.map((row) => {
                let value = row[mrIndex]; // Access the 'MR' column by index
    
                // Log each row for debugging
                //console.log(`Processing row ${index + 1}:`, row);
    
                if (typeof value !== 'undefined' && value !== null) {
                value = parseFloat(value.trim()); // Clean and parse the value
                } else {
                value = NaN; // Set to NaN if value is missing or undefined
                }
    
                if (isNaN(value)) {
                //console.warn(`Skipping invalid data at row ${index + 1}:`, value);
                return null; // Skip invalid data
                }
    
                return value;
            }).filter(value => value !== null); // Remove any null values
    
            // Check if there are any valid data points
            if (this.MR.length === 0) {
                throw new Error('No valid data found');
            }
    
            // Create time values for the x-axis based on index
            this.timeAxis = this.MR.map((_, index) => (index / 500).toFixed(2)); // 500 samples per second
    
            // Ensure DOM is ready before initializing the chart
            this.$nextTick(() => {
                setTimeout(() => {
                this.initializeChart();
                }, 100); // 100 ms delay to ensure DOM is fully rendered
            });
            } catch (error) {
            console.error('Error processing data:', error);
            // Optionally retry or handle the error
            }
        },
        initializeChart() {
         try {
            // Ensure the DOM element exists and log its dimensions
            const chartElement = document.getElementById('myChart');
            if (!chartElement) {
                throw new Error('Chart container not found');
            }
            console.log('Chart container dimensions:', chartElement.getBoundingClientRect());
    
            // Initialize ECharts instance
            const chart = echarts.init(chartElement);
    
            // Define chart options
            const option = {
                title: {
                    text: '0204451eFnorm: MR 5 min resampled to 500 Hz'
                },
                tooltip: {
                trigger: 'axis',
                axisPointer: {
                        type: 'cross'
                        },
                        borderWidth: 1,
                        borderColor: '#ccc',
                        padding: 10,
                        textStyle: {
                        color: '#000'
                        },
                        position: function (pos, params, el, elRect, size) {
                        const obj = {
                            top: 10
                        };
                        obj[['left', 'right'][+(pos[0] < size.viewSize[0] / 2)]] = 30;
                        return obj;
                        }
                        // extraCssText: 'width: 170px'
                },
                axisPointer: {
                        link: [
                        {
                            xAxisIndex: 'all'
                        }
                        ],
                        label: {
                        backgroundColor: '#777'
                        }
                },
                toolbox: {
                        feature: {
                        dataZoom: {
                            yAxisIndex: false
                        },
                        brush: {
                            type: ['lineX', 'clear'], 
                            title: {
                                lineX: 'Add event'
                            }
                        }
                        }
                },
                    brush: {
                        xAxisIndex: 'all',
                        brushLink: 'all',
                        outOfBrush: {
                        colorAlpha: 0.1
                        }
                    },
                    /*
                    visualMap: {},
                    */
                    grid: [
                        {
                        left: '10%',
                        right: '8%',
                        height: '50%'
                        },
                        {
                        left: '10%',
                        right: '8%',
                        top: '63%',
                        height: '16%'
                        }
                ],
                xAxis: {
                type: 'category',
                name: 'Time (s)',
                data: this.timeAxis, // Use timeAxis for the x-axis
                axisLabel: {
                    formatter: '{value}s' // Format x-axis labels to include 's' for seconds
                },
                },
                yAxis: {
                    type: 'value',
                    name: 'Amplitude (mV)',
                    scale: true,
                    splitArea: {
                        show: true
                    }
                },
                series: [{
                data: this.MR,
                type: 'line',
                showSymbol: false,
                smooth: true,  // Optionally make the line smooth
                lineStyle: {color: '#0000FF'},
                markArea: {
                    itemStyle: {
                    color: 'rgba(255, 173, 177, 0.4)'
                    },
                    data: [
                    [
                        {
                        name: 'Event 1',
                        xAxis: 37.27*500
                        },
                        {
                        xAxis: 40*500
                        }
                    ]
                    
                    ]
                }
                }]
            };
    
            // Set the options to the chart instance
            chart.setOption(option);
            
            // Mark chart as initialized
            this.chartInitialized = true;

            document.getElementById('add-event-button').addEventListener('click', () => {
                // Start a lineX brush selection
                chart.dispatchAction({
                    type: 'takeGlobalCursor',
                    key: 'brush',
                    brushOption: {
                        brushType: 'lineX',
                        brushMode: 'single' // 'single' for single selection, 'multiple' for multiple selections
                    }
                });
            });

            chart.on('brushSelected', this.handleBrushSelection);
            } catch (error) {
                console.error('Error initializing chart:', error);
            }
        }
    }
  };
  </script>
  
  <style>
  /* Ensure the chart container has a defined size */
  #myChart {
    width: 100%;
    height: 400px;
  }
  </style>
  