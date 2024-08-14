<template>
    <el-row :align="middle">
        <el-col>
            <el-image style="width: 100%; color:darkgrey; height: 100px" />
        </el-col>
    </el-row>
    <el-row :gutter="20">
            <el-col :span="6">
                <el-card style="max-width: 480px">
                    <h2>Events predicted</h2>

                    <p><u>Cycle 2</u></p>
                    <el-card class="text item">
                        <p v-if="edited"><i>Edited</i></p>
                        <el-button type="primary" round @click="zoomToEvent" style="margin-bottom: 10px">Event 1</el-button>
                        <el-row>
                            Start (s)   <el-input-number v-model="num1" placeholder="Start" :step="0.01" :min="0" :max="300" size="small" @change="handleChange(num1)" style="width: 100px; margin-bottom: 10px;"/>
                        </el-row>
                        <el-row>
                            End (s)   <el-input-number v-model="num2" :step="0.01" :min="0" :max="300" size="small" @change="handleChange(num2)" style="width: 100px"/>
                        </el-row>
                        <el-row>
                            <p><b>SDNN:</b>  4.2     <b>Duration: </b> 5 s</p>
                        </el-row>
                        <el-row>
                            Event type:     <el-button type="info" size="small" plain><el-icon><PriceTag /></el-icon> Phasic</el-button> <el-button type="info" size="small" plain>+ Add tag <el-icon><PriceTag /></el-icon></el-button>
                        </el-row>
                    </el-card>
                </el-card>
            </el-col>
            <el-col :span="18">
                <div>
                    <!-- Chart container -->
                    <div v-if="!chartInitialized">Loading chart...</div>
                    <el-button id="edit-button">Edit mode</el-button>
                    <el-button id="add-event-button">+ Add event</el-button>
                    <div id="myChart" style="width: 100%; height: 400px;"></div>
                    <el-row>
                        <el-label for="yValue" :span="2">Threshold:</el-label>
                        <input type="number" :span="5" id="yValue" :value="(0.1*this.mvc).toFixed(2)" step="0.2"/>
                        <el-button id="updateMarkLine" :span="4">Update Threshold</el-button>
                    </el-row>
                    <!-- Loading indicator -->
                    <div v-if="startSelection && endSelection"> Start: {{ startSelection }} s, End: {{ endSelection }} s , Duration: {{ duration }} s</div>
                </div>
            </el-col>
    </el-row>

  </template>
  
  <script>
  //import LineChart from '../components/LineChart.vue'
  import { ref } from 'vue'
  import * as echarts from 'echarts';
  import csv from '../assets/0204451eFnorm_MR_rms_5_min_resampled.csv'; // Adjust the path as needed
  import { PriceTag } from '@element-plus/icons-vue'

  export default {
    name: 'EventsClassificationPage',
    /*
    components: {
        LineChart
    },
    */
    data () {
        return {
            edited: false,
            num1: ref(37.27),
            num2: ref(40),
            MR: [],
            timeAxis: [],
            chartInitialized: false,
            startSelection: null,
            endSelection: null,
            duration: null,
            chart:null,
            mvc: 4.815170283983161,
            coords: [],
            amountEvents: 1
        }
    },
    components: {
        PriceTag
    },
    async mounted() {
      await this.processDataAndInitializeChart(); // Wait for data processing before initializing the chart
    },
    methods: {   
        handleChange(){
            this.updateChartArea()
            // TODO: Update in DB as well
            this.edited = true;
        },
        updateChartArea() {
            if (this.chart) {
                this.chart.setOption({
                    series: [{
                        markArea: {
                            data: [
                                [
                                    {
                                        name: 'Event 1',
                                        xAxis: this.num1 * 500
                                    },
                                    {
                                        xAxis: this.num2 * 500
                                    }
                                ]
                            ]
                        }
                    }]
                });
            }
        },
        zoomToEvent(){
            if (this.chart) {
                this.chart.dispatchAction({
                    type: 'dataZoom',
                    startValue: (this.num1 * 500) - (5*500),
                    endValue: (this.num2 * 500) + (5*500)
                });
            }
        },
        handleBrushSelection(params) {
            const selected = params.batch[0];
            if (selected) {
                const { areas } = selected;
                
                if (areas.length === 0){
                    this.startSelection = null;
                    this.endSelection = null;
                    this.duration = null;
                } else {
                    let startCoord = areas[0].coordRange[0];
                    let endCoord = areas[0].coordRange[1];
                    this.coords = areas[0].coordRange;

                    this.startSelection = (startCoord/500).toFixed(2);
                    this.endSelection = (endCoord/500).toFixed(2);
                    this.duration = (this.endSelection - this.startSelection).toFixed(2);
                }
            }
        },
        async transformBrushToMarkArea(){
            console.log("coords: ", this.coords)
            if (this.coords) {      
                this.amountEvents++;
                
                const option = this.chart.getOption();
                if (!option.series || option.series.length === 0) {
                    console.error('No series found in chart options');
                    return;
                }
                // Initialize markArea if not present
                option.series[0].markArea = option.series[0].markArea || { data: [] };

                // Add new markArea
                option.series[0].markArea.data.push(
                    [
                        {
                            name: 'Event ' + this.amountEvents,
                            xAxis: this.coords[0],
                            yAxisIndex: 0,
                            xAxisIndex: 0 
                        },
                        {
                            xAxis: this.coords[1],
                            yAxisIndex: 0,
                            xAxisIndex: 0 
                        }
                    ]
                );

                
                console.log("OPTIONS")
                console.log(option)
                this.chart.setOption(option)

                this.chart.dispatchAction({
                    type: 'takeGlobalCursor',
                    key: 'brush',
                    brushOption: {
                        title: { lineX: 'Brush' },
                        show: false // Hide the brush tool button
                    }
                });
                
                this.chart.dispatchAction({
                    type: 'brush',
                    command: 'clear',
                    areas: []
                });
                

                // Reset coords
                this.coords = [];
                
            } else {
                console.warn('No brush area selected.');
            }
        },
        async processDataAndInitializeChart() {
            try {
            //console.log("CSV Data:", csv);
    
            // First row is the header
            const header = csv[0];
            const mrIndex = header.indexOf('MR'); // Find the index of the 'MR' column
    
            if (mrIndex === -1) {
                throw new Error('Column "MR" not found in header');
            }
    
            // Remove empty rows
            const filteredRows = csv.slice(1).filter(row => row.length > 1);
    
            // Extract and clean the 'MR' column from the filtered data
            this.MR = filteredRows.map((row) => {
                let value = row[mrIndex]; // Access the 'MR' column by index

                //console.log(`Processing row ${index + 1}:`, row);
    
                if (typeof value !== 'undefined' && value !== null) {
                value = parseFloat(value.trim()); // Clean and parse the value
                } else {
                value = NaN; // Set to NaN if value is missing or undefined
                }
    
                if (isNaN(value)) {
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
            }
        },
        initializeChart() {
         try {
            const chartElement = document.getElementById('myChart');
            if (!chartElement) {
                throw new Error('Chart container not found');
            }
            console.log('Chart container dimensions:', chartElement.getBoundingClientRect());
            const chart = echarts.init(chartElement);
            this.chart=chart;

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
                    grid: [
                        {
                        left: '10%',
                        right: '7%',
                        height: '50%',
                        width: '80%'
                        }
                ],
                xAxis: {
                type: 'category',
                name: 'Time (s)',
                data: this.timeAxis,
                axisLabel: {
                    formatter: '{value}s'
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
                smooth: true,
                //lineStyle: {color: '#0000FF'},
                markArea: {
                    itemStyle: {
                        color: '#d0aee5'
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
                },
                markLine: {
                    data: [
                        {
                            yAxis: (0.1*this.mvc).toFixed(2), // Set the threshold value here
                            label: {
                                formatter: 'Threshold', // Customize label
                                position: 'start', // Position label at the end of the line
                            },
                            lineStyle: {
                                color: 'red', // Customize line color
                                type: 'dashed' // Customize line type (solid, dashed, dotted, etc.)
                            }
                        }
                    ]
                }
                }],
            };
    
            chart.setOption(option);
            
            this.chartInitialized = true;

            document.getElementById('edit-button').addEventListener('click', () => {
                chart.dispatchAction({
                    type: 'takeGlobalCursor',
                    key: 'brush',
                    brushOption: {
                        brushType: 'lineX',
                        brushMode: 'single'
                    }
                });
            });

            // Update the markLine position
            document.getElementById('updateMarkLine').addEventListener('click', function () {
                var yValue = document.getElementById('yValue').value;
                chart.setOption({
                    series: [{
                        markLine: {
                        data: [
                            {
                                yAxis: parseFloat(yValue), // Set the threshold value here
                                label: {
                                    formatter: 'Threshold', // Customize label
                                    position: 'start', // Position label at the end of the line
                                },
                                lineStyle: {
                                    color: 'red', // Customize line color
                                    type: 'dashed' // Customize line type (solid, dashed, dotted, etc.)
                                }
                            }
                        ]
                }}]
                });
            });


            chart.on('brushSelected', this.handleBrushSelection);

            // Add button event listener
            document.getElementById('add-event-button').addEventListener('click', () => {
                this.transformBrushToMarkArea();
            });

            // Add event listener for click
            chart.on('click', (params) => {
                console.log('Params: ', params)
                console.log("CIAO")
                // Check if the click is within a marked area
                if (params.componentType === 'markArea' && params.seriesType === 'line') {
                    console.log(params.data.coord[0][0], params.data.coord[1][0])
                }
            });

            } catch (error) {
                console.error('Error initializing chart:', error);
            }
        }
    }

  }
  </script>

<style>
/* Ensure the chart container has a defined size */
#myChart {
  width: 100%;
  height: 400px;
}
</style>
