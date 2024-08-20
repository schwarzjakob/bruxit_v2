<template>
    <!--HEADER ROW-->
    <el-row style="margin-top: 10px;">
        <el-col :span="2"><el-button type="primary"> <el-icon> <ArrowLeft /> </el-icon> Sleep Stage Detection</el-button></el-col>
        <el-col :span="1" :offset="2"><el-tag type="success" size="large">Advanced</el-tag></el-col>
        <el-col :span="13" :offset="1"><PipelineStepper :step="3"/></el-col>
        <el-col :span="2" :offset="1"><el-button type="primary"> Monitoring Dashboards  <el-icon> <ArrowRight /> </el-icon></el-button></el-col>
    </el-row>

    <!--IMAGE ROW-->
    <el-row justify="center">
        <h2> Patient 1, w1, night 1022102</h2>
    </el-row>
    <el-row justify="center">
        <h3>Signal and predicted events</h3>
        <el-button type="info" @click="toggleImage" style="margin-left: 20px; margin-top: 10px" plain>
        {{ isImageVisible ? 'Hide' : 'Show' }} Image
        </el-button>    
    </el-row>
    <el-row justify="center">
        <el-image v-if="isImageVisible" :src="nightPredImg" style="max-width: 900px" :preview-src-list="[nightPredImg]" fit="cover"/>
    </el-row>

    <el-row :gutter="20">
        <!--EVENTS PREDICTED ZONE-->
        <el-col :span="6">
            <el-card style="max-width: 480px">
                <h2>Events predicted</h2>

                <p><u>Cycle 2</u></p>
                <el-card class="text item" v-for="i in parseInt(amountEvents)" :key="i" :style="amountEvents === 2 ? specialStyle: ''">
                    <p v-if="edited"><i>Edited</i></p>
                    <div>
                    <el-button type="primary" round @click="zoomToEvent" style="margin-bottom: 10px; margin-right: 200px;"><el-tooltip content="Click to zoom" placement="top">Event {{ i }}</el-tooltip></el-button>
                        <el-popover
                            placement="top-start"
                            :title="`Event ${i}`"
                            :width="200"
                            trigger="hover"
                        >
                            <b>Amplitude</b><br>
                            Min: 0.17 mV <br>   Max: 1.41 mV  <br>  Median: 0.60 mV<br>
                            <b>ECG Rate</b><br>
                            Min: 72.31 bpm  <br>  Max: 76.42 bpm  <br>  Median: 74.07 bpm<br>
                            <b>HRV Metrics</b><br>
                            LF/HF (5 min): <br>Mean (5 min):<br> SD (90 min): <br>SD (5 min): <br>SD (5 s before & after event): <br>SD (event): 

                            <template #reference>
                                <el-icon size="large" color='#409EFF'><InfoFilled /></el-icon>
                            </template>
                        </el-popover>
                    </div>  

                    <div style="margin-left: 10px;">
                        <el-row>
                            <div>
                                Start (s)   <el-input-number v-model="num1" placeholder="Start" :step="0.01" :min="0" :max="300" size="small" @change="handleChange(num1)" style="width: 100px; margin-bottom: 10px; margin-left: 5px;"/>
                            </div>
                            <div>
                                End (s)   <el-input-number v-model="num2" :step="0.01" :min="0" :max="300" size="small" @change="handleChange(num2)" style="width: 100px; margin-bottom: 10px; margin-left: 10px;"/>
                            </div>
                        </el-row>
                        <el-row>
                            <p><b>SD (event):</b>  4.2   <b style="margin-left: 10px;">Duration: </b> 5 s</p>
                        </el-row>
                        <el-row>
                            <div>
                                Event type:     <el-button type="info" size="small" plain style="margin-left: 10px;"><el-icon><PriceTag /></el-icon> Phasic</el-button> <el-button type="info" size="small" plain>+ Add tag <el-icon><PriceTag /></el-icon></el-button>
                            </div>
                        </el-row>
                        <el-row>
                            <el-switch
                                v-model="event1Confirm"
                                class="mb-2"
                                style="--el-switch-on-color: #13ce66; --el-switch-off-color: #ff4949; margin-left: 40%; margin-top: 20px;"
                                active-text="Confirm"
                                inactive-text="Discard"
                            />
                        </el-row>
                        <el-row v-if="event1Confirm">
                            <div style="margin-top: 5px; margin-left: 40%;">Include: </div>
                            <el-checkbox-group v-model="checkboxGroup" style="margin-left: 10px;">
                                <el-checkbox-button v-for="sensor in sensors" :key="sensor" :value="sensor">
                                    {{sensor}}
                                </el-checkbox-button>
                            </el-checkbox-group>
                        </el-row>
                    </div>
                </el-card>
            </el-card>

            <el-button style=" margin-top: 10px; width: 380px" type="primary" >
                <el-icon> <Refresh /> </el-icon> Retrain model
            </el-button>
    
        </el-col>

        <!--CHARTS ZONE-->
        <el-col :span="17">
            <el-row>
                <div style="margin-left: 10px">
                <el-label for="yValue" :span="2" style="margin-right: 10px; margin-top: 5px;">Threshold:</el-label>
                <el-input type="number" v-model="threshold" :span="5" id="yValue"  step="0.2" style="margin-right: 10px; width:100px"/>
                <el-button id="updateMarkLine" :span="4">Update Threshold</el-button>
                </div>
                <div style="margin-left: 30%;">
                    <el-checkbox-group v-model="checkboxGroup2" style="margin-left: 10px;">
                        <el-checkbox-button v-for="sensor in sensors" :key="sensor" :value="sensor">
                            {{sensor}}
                        </el-checkbox-button>
                    </el-checkbox-group>
                </div>

                <div style="margin-left: 30px">
                    <el-button id="edit-button" :plain="true" :type="buttonType" @click="clickButton">
                        Edit Mode
                    </el-button>
                </div>
                <div v-if="selectionActive && startSelection && endSelection" style="margin-left: 30px">
                    <el-popover
                        placement="bottom"
                        title="Add event"
                        :width="250"
                        trigger="click"
                        content="this is content, this is content, this is content"
                    >
                    <el-form :model="eventForm" class="form-container">
                        <el-form-item label="Start (s)">
                        <el-input-number v-model="eventForm.start" :min="0" label="Start Time" />
                        </el-form-item>
                        <el-form-item label="End (s)">
                        <el-input-number v-model="eventForm.end" :min="0" label="End Time" />
                        </el-form-item>
                        <b>Duration: {{ (eventForm.end - eventForm.start).toFixed(2)}} s</b>
                        <el-form-item style="margin-top: 5px;">
                        <el-button type="primary" @click="submitForm">Submit</el-button>
                        </el-form-item>
                    </el-form>
                        <template #reference>
                        <el-badge is-dot class="item">
                           <el-button class="m-2" @click="updateSelectionValues">+ Add</el-button> 
                        </el-badge>
                        </template>
                    </el-popover>
                </div>
                <div style="margin-left: 30px">
                    <el-button id="zoom-button" :plain="true" :disabled="zoomDisabled">
                        Zoom
                    </el-button>    
                </div>
            </el-row>

            <div v-if="!chartInitialized">Loading chart...</div>

            <div id="myChart" style="width: 100%; height: 550px; margin-top: 10px"></div>
            <!-- Loading indicator -->
            <div v-if="startSelection && endSelection"> Start: {{ startSelection }} s, End: {{ endSelection }} s , Duration: {{ duration }} s</div>
        </el-col>
    </el-row>
  </template>
  
  <script>
  import { ref } from 'vue'
  import * as echarts from 'echarts';
  import csv from '../assets/1022102cFnorm_rms_5_min_256Hz.csv'; // Adjust the path as needed
  import { PriceTag, Refresh, InfoFilled } from '@element-plus/icons-vue'
  import img from '../../../backend/src/data/p1_wk1/1022102.png'
  import { reactive } from 'vue'
  import PipelineStepper from '../components/PipelineStepper.vue'
  


  export default {
    name: 'ECPage',
    data () {
        return {
            edited: false,
            num1: ref(37.27),
            num2: ref(40),
            MR: [],
            ECG: [],
            timeAxis: [],
            threshold: ref((0.1*5).toFixed(2)),
            chartInitialized: false,
            startSelection: null,
            endSelection: null,
            duration: null,
            chart:null,
            mvc: 5,
            coords: [],
            amountEvents: 1,
            nightPredImg: img,
            isImageVisible: true,
            sensors: ['MR', 'ML'],
            checkboxGroup: ref(['MR']),
            checkboxGroup2: ref(['MR']),
            event1Confirm: ref(true),
            buttonType: "",
            selectionActive: false,
            showSelectionDialog: false,
            zoomDisabled: false,
            eventForm: reactive({
                        start: 0,
                        end: 0,
                        }),
            specialStyle: {
                marginBottom: "10px",
                borderColor: "#409EFF"
            }
        }
    },
    components: {
        PriceTag,
        Refresh,
        InfoFilled,
        PipelineStepper
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
                                        xAxis: this.num1 * 256
                                    },
                                    {
                                        xAxis: this.num2 * 256
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
                    startValue: (this.num1 * 256) - (5*256),
                    endValue: (this.num2 * 256) + (5*256)
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

                    this.startSelection = (startCoord/256).toFixed(2);
                    this.endSelection = (endCoord/256).toFixed(2);
                    this.duration = (this.endSelection - this.startSelection).toFixed(2);
                }
            }
        },
        async markEvent(start, end){
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
                        xAxis: Math.floor(start*256),
                        yAxisIndex: 0,
                        xAxisIndex: 0 
                    },
                    {
                        xAxis: Math.floor(end*256),
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
            const ecgIndex = header.indexOf('ECG');
            if (mrIndex === -1) {
                throw new Error('Column "MR" not found in header');
            }

            if (ecgIndex === -1) {
                throw new Error('Column "ECG" not found in header');
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
                throw new Error('No valid MR data found');
            }

            // Extract and clean the 'ECG' column from the filtered data
            this.ECG = filteredRows.map((row) => {
                let value = row[ecgIndex]; // Access the 'MR' column by index

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
            if (this.ECG.length === 0) {
                throw new Error('No valid ECG data found');
            }

    
            // Create time values for the x-axis based on index
            this.timeAxis = this.MR.map((_, index) => parseInt(index / 256)); // 256 samples per second
            console.log("TIME: ", this.timeAxis)

            // Ensure DOM is ready before initializing the chart
            this.$nextTick(() => {
                setTimeout(() => {
                this.initializeMRChart();
                }, 100); // 100 ms delay to ensure DOM is fully rendered
            });
            } catch (error) {
                console.error('Error processing data:', error);
            }
        },
        initializeMRChart() {
         try {
            const chartElement = document.getElementById('myChart');
            if (!chartElement) {
                throw new Error('Chart container not found');
            }
            console.log('Chart container dimensions:', chartElement.getBoundingClientRect());
            const chart = echarts.init(chartElement);
            this.chart=chart;

            let events = [{'start': 37.27*256, 'end': 40*256}]

            // Define chart options
            const option = {
                legend: {
                    data: ['MR', 'ECG Rate'],
                    right: 10,
                    top: 60,
                    orient: 'vertical'
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
                    },
                    formatter: function (params) {
                        if (params !== undefined) {  
                            params.sort((a, b) => a.seriesIndex - b.seriesIndex);
                            let title = "" 
                            let startEvent = null
                            let endEvent = null
                            console.log("PARAMS: ", params)
                            let xPoint = params[0].dataIndex;
                            let yPoint = params[0].value;

                            //console.log(xPoint, yPoint)

                            for (const i in events) {
                                //console.log(events[i])
                                if (events[i]['start'] <= xPoint && events[i]['end'] >= xPoint){
                                    title = "Event " + parseInt(i+1)
                                    console.log("dentro")

                                    startEvent = events[i]['start']
                                    endEvent = events[i]['end']
                                }
                            }


                            //const seriesName = params[0].seriesName || '';

                            // Format the value to 2 decimal places
                            const formattedValue = yPoint.toFixed(2);

                            // Return the tooltip HTML
                            return `
                                ${title ? `<strong>${title}</strong><br>Start: ${(startEvent/256).toFixed(2)} s, End: ${(endEvent/256).toFixed(2)} s<br>Duration: ${(endEvent/256-startEvent/256).toFixed(2)} s<br>Fmean: 500 Hz<br>Fmedian: 400 Hz<hr>` : ''}
                                ${params[0].marker}  <b>MR</b> : ${formattedValue} mV<br>
                                <hr>
                                ${params[1].marker} <b>ECG</b> : ${params[1].value.toFixed(2)} bpm<br>
                                LF/HF (5 min): 0.33<br>
                                Mean (5 min)<br>
                                SD (5 min): 5<br>
                                SD (Sleep cycle 2 (90 min)): 6<br>
                                ${title ? `SD (5 s before & after event): 7<br>SD (during event): 3` : ''}
                                <hr>
                                t: ${(xPoint/256).toFixed(2)} s<br>
                                Sampling Rate: 256 Hz<br>
                                Sleep cycle: 2<br>
                            `;

                        }
                            
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
                    dataZoom: [
                        /*
                        {
                            type: 'slider',
                            xAxisIndex: [0, 1, 2], // Link both x-axes
                        },
                        */
                        {
                            type: 'inside',
                            xAxisIndex: [0, 1, 2], // Link both x-axes
                            zoomOnMouseWheel: false,
                        }
                    ],
                    
                    grid: [
                    { left: '10%', right: '10%', top: '5%', height: '50%' },  // MR
                    { left: '10%', right: '10%', top: '68%', height: '18%' }, // ecg
                ],
                xAxis: [{
                    gridIndex: 0,
                type: 'category',
                name: 'Time (s)',
                data: this.timeAxis,
                axisLabel: {
                    formatter: '{value}s',
                    interval: 25*256
                },
                },
                {
                    gridIndex: 1,
                    type: 'category',
                    name: 'Time (s)',
                    data: this.timeAxis,
                    axisLabel: {
                        formatter: '{value}s',
                        interval: 25*256
                    },
                },],
                yAxis: [{
                    gridIndex: 0,
                    type: 'value',
                    name: 'Amplitude (mV)',
                    scale: true,
                    splitArea: {
                        show: true
                    }
                },  {
                    gridIndex: 1,
                    type: 'value',
                    name: 'Beats per minute (bpm)',
                    scale: true,
                    splitArea: {
                        show: true
                    },
                    min: 0
                    
                }, {
                    gridIndex: 1,
                    type: 'value',
                    name: 'HRV Metrics',
                    scale: true,
                    splitArea: {
                        show: true
                    },
                    min:0
            }],

                series: [{
                    name: 'MR',
                    data: this.MR,
                    type: 'line',
                    xAxisIndex: 0,
                    yAxisIndex: 0,
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
                            xAxis: 37.27*256
                            },
                            {
                            xAxis: 40*256
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
                }, 
                {
                        name: "ECG Rate",
                        data: this.ECG,
                        type: 'line',
                        xAxisIndex: 1,
                        yAxisIndex: 1,
                        showSymbol: false,
                        smooth: true,
                        lineStyle: {color: '#008000'},
                        markArea: {
                            itemStyle: {
                                color: '#d0aee5'
                            },
                            data: [
                            [
                                {
                                name: '',
                                xAxis: 37.27*256
                                },
                                {
                                xAxis: 40*256
                                }
                            ]
                            
                            ]
                        },
                }, {
                        name: "HRV",
                        data: Array.from({ length: 100 }, (v, i) => i),
                        type: 'line',
                        xAxisIndex: 1,
                        yAxisIndex: 2,
                        showPointer: false,
                        showSymbol: false,
                        smooth: true,
                        lineStyle: {color: '#008000'},
                        markLine: {
                            data: [
                                {
                                    //type: 'average',
                                    name: 'LF/HF',
                                    yAxis: (1.46168046835356).toFixed(2),
                                    lineStyle: {
                                        color: 'blue',
                                        type: 'dashed',
                                        width: 2,
                                    },
                                    label: {
                                        position: 'middle'
                                    }
                                },
                                {
                                    yAxis: (76.5601888310285).toFixed(2),
                                    name: 'SD',
                                    lineStyle: {
                                        color: 'orange',
                                        type: 'dashed',
                                        width: 2,
                                    },
                                    label: {
                                        position: 'middle',
                                        distance:0
                                    }
                                },
                            ],
                            label: {
                                formatter: '{b}: {c}'
                            }
                        },
                        
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

            document.getElementById('zoom-button').addEventListener('click', () => {
                chart.dispatchAction({
                    type: 'takeGlobalCursor',
                    key: 'dataZoom',
                });
            });

            chart.on('dataZoom', (params) => {
                console.log('DataZoom triggered', params);
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

            // Add event listener for double-click
            chart.getZr().on('dblclick', function (params) {
                const pointInPixel = [params.offsetX, params.offsetY];
                const pointInGrid = chart.convertFromPixel({ seriesIndex: 0 }, pointInPixel);

                console.log(pointInGrid)

                const series = option.series[0];
                const markAreas = series.markArea.data;

                let isInMarkArea = false;

                console.log(markAreas)

                for (const i in events) {
                    //console.log(events[i])
                    if (events[i]['start'] <= pointInGrid[0] && events[i]['end'] >= pointInGrid[0]){
                        isInMarkArea = true;
                        console.log("DENTRONE")
                        chart.dispatchAction({
                            type: 'dataZoom',
                            startValue: (events[i]['start'] ) - (5*256),
                            endValue: (events[i]['end']) + (5*256)
                        });
                    }
                    
                }

                if (!isInMarkArea) {
                    chart.dispatchAction({
                    type: 'dataZoom',
                    start: 0,
                    end: 100
                });
                }
            });

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
        },
        toggleImage() {
            this.isImageVisible = !this.isImageVisible; // Toggle the visibility
        },
        clickButton() {
            this.selectionActive = !this.selectionActive;

            if(this.selectionActive){
                this.buttonType = "primary"
                this.zoomDisabled = true
            } else {
                this.buttonType = ""
                this.zoomDisabled = false
            }
        },
        triggerSelectionDialog(){
            this.showSelectionDialog = !this.showSelectionDialog;
        },
        async submitForm(){
            await this.markEvent(this.eventForm.start, this.eventForm.end)
        },
        updateSelectionValues(){
            this.eventForm.start = this.startSelection;
            this.eventForm.end = this.endSelection;
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
