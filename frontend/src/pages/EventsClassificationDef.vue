<template>
    <el-row style="margin-top: 10px;">
        <el-col :span="2"><router-link :to="'/patient-data/'"><el-button type="primary"> <el-icon> <ArrowLeft /> </el-icon> Patient Data</el-button></router-link></el-col>
        <el-col :span="1" :offset="2"><el-tag type="success" size="large">Advanced</el-tag></el-col>
        <el-col :span="13" :offset="1"><PipelineStepper :step="2" /></el-col>
        <el-col :span="2" :offset="1"><router-link :to="'/monitoring/'"><el-button type="primary"> Monitoring Dashboards  <el-icon> <ArrowRight /> </el-icon></el-button></router-link></el-col>
    </el-row>

    <!--IMAGE ROW-->
    <el-row justify="center"> <h1>Patient {{ this.$store.state.patientId }}, Week {{ this.$store.state.weekId }}, file {{ this.$store.state.file }}, size {{ this.$store.state.fileSize }} GB</h1></el-row>

    <el-row justify="center">
        <h2>Signal and predicted events</h2>
        <el-button type="info" @click="toggleImage" style="margin-left: 20px; margin-top: 10px" plain>
        {{ isImageVisible ? 'Hide' : 'Show' }} Image
        </el-button>    
    </el-row>
    <el-row justify="center">
        <el-image v-if="isImageVisible" :src="nightPredImg" style="max-width: 900px" :preview-src-list="[nightPredImg]" fit="cover"/>
    </el-row>

    <el-row>
        <el-col :offset="18">
            <div id="ec-heatmap" style="width: 560px; height: 500px;"></div>
        </el-col>
    </el-row>

    <el-row>
        <el-col :span="5" v-loading="!emgReceived">
            <el-card>
                <div v-if="amountEvents === 0">
                    No events predicted during currently selected frame.
                </div>
                <div v-else>
                    <el-card class="text item" v-for="(value, key) in current5minEvents" :key="key">
                        <el-button type="primary" round @click="zoomToEvent(key, value)" style="margin-bottom: 10px; margin-right: 200px;">
                            <el-tooltip content="Click to zoom" placement="top">Event {{ key.slice(1) }}</el-tooltip>
                        </el-button>
                        <el-popover
                            placement="top-start"
                            :title="`Event ${key.slice(1)}`"
                            :width="200"
                            trigger="hover"
                        >
                            <b>EMG Metrics</b><br>
                            Avg. RMS MR: {{ (value.rms_mr).toFixed(2) }}<br>
                            Avg. RMS MR: {{ (value.rms_ml).toFixed(2) }}<br>
                            Avg. St. dev. MR : {{ (value.std_mr).toFixed(2) }} <br>
                            Avg. Std. dev. ML {{ (value.std_ml).toFixed(2) }} <br>
                            <b>HRV Metrics</b><br>
                            LF/HF MR: {{ (value.HRV_lf_hf).toFixed(2) }} <br>Mean: {{ (value.HRV_mean).toFixed(2) }}<br> SD: {{ (value.HRV_sdnn).toFixed(2) }} <br>

                            <template #reference>
                                <el-icon size="large" color='#409EFF'><InfoFilled /></el-icon>
                            </template>
                        </el-popover>
                        <!--BOTTOM PART CARD-->
                        <div style="margin-left: 10px;">
                        <el-row>
                            <div>
                                Start (s)   <el-input-number v-model="value.start_s" placeholder="Start" :step="0.01" :min="Math.min(...emgTime)" :max="Math.max(...emgTime)" size="small" @change="handleChange(key, value)" style="width: 120px; margin-bottom: 10px; margin-left: 5px;"/>
                            </div>
                            <div>
                                End (s)   <el-input-number v-model="value.end_s" :step="0.01" :min="Math.min(...emgTime)" :max="Math.max(...emgTime)" size="small" @change="handleChange(key, value)" style="width: 120px; margin-bottom: 10px; margin-left: 10px;"/>
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
                            <el-radio-group v-model="radioValues[key]" size="large" fill="#13ce66" style="margin-left: 40%; margin-top: 20px;">
                                <el-radio-button label="Discard" :value="0" />
                                <el-radio-button label="Confirm" :value="1" />
                            </el-radio-group>
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
                </div>
            </el-card>
        </el-col> 
        <el-col :span="1" style="margin-top:300px">
            <el-button type="primary" circle @click="moveBackward()"><el-icon><ArrowLeft /></el-icon></el-button>
        </el-col>
        <el-col :span="14" v-loading="!emgReceived" element-loading-text="Loading the data...">
            <div id="emg-chart" style="width: 100%; height: 600px;"></div>
        </el-col>
        <el-col :span="1" style="margin-top:300px">
            <el-button type="primary" circle @click="moveForward()"><el-icon><ArrowRight /></el-icon></el-button>
        </el-col>
        
    </el-row>

  </template>
  
  <script>
  import img from '../assets/NightOverview.png'
  import PipelineStepper from '../components/PipelineStepper.vue'
  import * as echarts from 'echarts';
  import { markRaw } from 'vue';
  import axios from 'axios';
  import {ArrowRight, ArrowLeft} from '@element-plus/icons-vue'

  export default {
    name: 'EventsClassificationDef',
    components: {
        PipelineStepper,
        ArrowRight,
        ArrowLeft
    },
    async mounted(){
        await this.getPredictions();
        await this.getData((0).toFixed(2));
        this.drawECHeatMap();
    },
    data () {
        return {
            isImageVisible: true,
            nightPredImg: img,
            mr: [],
            ml: [],
            emgTime: [],
            selectedInterval: [[0,0,0]],
            emgReceived: false,
            cancelToken: null,
            tileIndex: (0).toFixed(2),
            predictions: {},
            current5minEvents: {},
            amountEvents: 0,
            emgChart: null,
            radioValues: {},
            emgDataLengthS: 0
        }
    },
    methods: {
        toggleImage() {
            this.isImageVisible = !this.isImageVisible;
        },
        handleChange(key, value){
            console.log(value.start_s, value.end_s)
        },
        async moveForward(){
            this.tileIndex = (parseFloat(this.tileIndex) + 0.50).toFixed(2)
            console.log(this.selectedInterval.length)
            if(this.selectedInterval.length == 1){
                console.log(this.selectedInterval[0])
                let xCurrent = this.selectedInterval[0][0]
                let yCurrent = this.selectedInterval[0][1]
                let value = this.selectedInterval[0][2]
                console.log(xCurrent, yCurrent, value)
                console.log(typeof xCurrent, typeof yCurrent, typeof value)

                if (xCurrent == 17){
                    yCurrent = yCurrent +1
                    xCurrent = 0
                } else {
                    xCurrent = xCurrent + 1
                }
                this.selectedInterval.push([xCurrent, yCurrent, value])
                console.log(this.selectedInterval)
            }
            else if(this.selectedInterval.length == 2){
                this.selectedInterval.shift();
                console.log(this.selectedInterval)
            }
            this.drawECHeatMap();
            await this.getData(this.tileIndex);
        },
        async moveBackward(){
            console.log("move backward")
        },
        async getData(idx) {
            this.emgReceived = false;

            const nd_path = `http://127.0.0.1:5000/night-duration/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}`;

            const path = `http://127.0.0.1:5000/get-emg/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}/${idx}`;
            const headers = {
                Accept: 'application/json',
                'Content-Type': 'application/json',
            };


            // Cancel the previous request if it exists
            if (this.cancelToken) {
                this.cancelToken.cancel('Previous request canceled due to new click.');
            }

            // Create a new cancel token for the new request
            this.cancelToken = axios.CancelToken.source();

            try {
                await axios.get(nd_path, {headers})
                .then((res) => {
                    this.emgDataLengthS = res.data.duration_s;
                    console.log("duration s: ", res.data.duration_s)

                })
                .catch(err=>{
                    console.log(err)
                })

                const res = await axios.get(path, {
                headers,
                cancelToken: this.cancelToken.token, // Attach the cancel token
                });

                console.log(res.data);
                this.mr = res.data.MR;
                this.ml = res.data.ML;
                this.emgTime = res.data.EMG_t;
                this.emgReceived = true;
                let events = this.mapEventTimesToEmgTimeInRange(this.predictions, res.data.EMG_t);
                console.log(events)
                console.log(Object.keys(events).length)
                this.current5minEvents = events;
                if(Object.keys(events).length >0){
                    this.amountEvents = Object.keys(events).length;
                    console.log("amount: ", this.amountEvents)
                }
                for (const key of Object.keys(events)){
                    console.log(key)
                    this.radioValues[key] = 1
                }
                
                this.drawEMGLinePlot(); // Function to draw the EMG plot with the fetched data
            } catch (error) {
                if (axios.isCancel(error)) {
                console.log('Previous request canceled:', error.message);
                } else {
                console.log(error);
                }
            }
        },
        mapEventTimesToEmgTimeInRange(events, emgTime) {
            const emgTimeMin = Math.min(...emgTime);
            const emgTimeMax = Math.max(...emgTime);

            console.log("min: ", emgTimeMin)
            console.log("max: ", emgTimeMax)
            events = events.replace(/NaN/g, 'null');
            events = JSON.parse(events)
            console.log(typeof events)

            // Helper function to find the closest value in the emgTime array
            function findClosest(time, emgTime) {
                return emgTime.reduce((prev, curr) => (Math.abs(curr - time) < Math.abs(prev - time) ? curr : prev));
            }

            // Map start_s and end_s to the closest values in emgTime only if within range
            const mappedEvents = Object.keys(events).reduce((mapped, eventKey) => {
                const event = events[eventKey];
                //console.log(event)
                // Only map if both start_s and end_s are within the emgTime range
                if (event.start_s >= emgTimeMin && event.end_s <= emgTimeMax) {
                const closestStart = findClosest(event.start_s, emgTime);
                const closestEnd = findClosest(event.end_s, emgTime);

                // Create a new object with mapped start_s and end_s
                mapped[eventKey] = {
                    ...event,
                    start_s: closestStart,
                    end_s: closestEnd,
                };
                }

                return mapped;
            }, {});

            return mappedEvents;
        },
        async getPredictions(){
            this.loading = true;
            const path = `http://127.0.0.1:5000/predict-events/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}`
            const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            };

            await axios.get(path, {headers})
                .then((res) => {
                    this.predictions = res.data;
                    console.log("Predictions")
                    console.log(res.data)

                })
                .catch(err=>{
                    console.log(err)
                })
        },
        /*
        zoomToEvent(key, value){
            if (this.emgChart) {
                //this.basicStyle = {}
                let min = Math.min(...this.emgTime)
                let max = Math.ceil(Math.max(...this.emgTime))
                const start = parseFloat(value['start_s']);
                const end = parseFloat(value['end_s']);
                const startNorm = ((start - min) / (max-min)) * (300-0) + 0
                const endNorm = ((end - min) / (max-min)) * (300-0) + 0

                console.log(startNorm, endNorm)
                this.emgChart.dispatchAction({
                    type: 'dataZoom',
                    startValue: (startNorm*200) - (5*200),
                    endValue: (endNorm*200) - (5*200)
                });
            }
        },
        */
        async drawEMGLinePlot(){
            let emgChart = markRaw(echarts.init(document.getElementById('emg-chart')));
            this.emgChart = emgChart;
            let events = this.mapEventTimesToEmgTimeInRange(this.predictions, this.emgTime);
            this.current5minEvents = events;
            console.log(this.predictions)
            console.log("events in 5 min: ", events)
            let markAreaData = [];

            let min = Math.min(...this.emgTime)
            let max = Math.ceil(Math.max(...this.emgTime))

            
            for (const [key, value] of Object.entries(events)){
                const start = parseFloat(value['start_s']);
                const end = parseFloat(value['end_s']);
                const startNorm = ((start - min) / (max-min)) * (300-0) + 0
                const endNorm = ((end - min) / (max-min)) * (300-0) + 0
                markAreaData.push([{ name: key, xAxis: startNorm*200}, { xAxis: endNorm*200}]);
            }
            console.log("markarea: ", markAreaData)
            let option;

            option = {
                legend: {
                    data: ['MR', 'ML'],
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
                            //console.log("PARAMS: ", params)
                            console.log(option)
                            //let xPoint = params[0].dataIndex;
                            let yPoint = params[0].value;
                            //console.log(this.tileIndex)
                            //let factor = this.tileIndex + 1.00
                            const formattedValue = yPoint.toFixed(2);

                            // Return the tooltip HTML
                            return `
                                ${params[0].marker}  <b>MR</b> : ${formattedValue} V<br>
                                <hr>
                                ${params[1].marker} <b>ML</b> : ${params[1].value.toFixed(2)} V<br>
                                LF/HF (5 min): 0.33<br>
                                Mean (5 min)<br>
                                SD (5 min): 5<br>
                                SD (Sleep cycle 2 (90 min)): 6<br>
                                ${title ? `SD (5 s before & after event): 7<br>SD (during event): 3` : ''}
                                <hr>
                                t: ${(parseFloat(params[0].axisValue)).toFixed(2)} s<br>
                                Sampling Rate: 200 Hz<br>
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
                            type: ['lineX', 'clear']
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
                    {
                        type: 'slider',
                        xAxisIndex: [0, 1], // Link both x-axes
                    },
                    {
                        type: 'inside',
                        xAxisIndex: [0, 1], // Link both x-axes
                        zoomOnMouseWheel: false,
                    }
                ],
                grid: [
                    {
                    left: 60,
                    right: 50,
                    height: '40%',
                    bottom: 320
                    },
                    {
                    left: 60,
                    right: 50,
                    top: '55%',
                    height: '40%',
                    }
                ],
                /*
                visualMap: {
                    show: false,
                    seriesIndex: 5,
                    dimension: 2,
                    pieces: [
                    {
                        value: 1,
                        color: downColor
                    },
                    {
                        value: -1,
                        color: upColor
                    }
                    ]
                },
                */
                xAxis: [
                    {
                    type: 'category',
                    data: this.emgTime,
                    gridIndex: 0,
                    name: 'Time (s)',
                    axisLabel: {
                        interval: (index) => {
                            // Only show every 25-second label on the x-axis
                            return index % (25 * 200) === 0;
                        },
                        },
                        axisTick: {
                        alignWithLabel: true,
                        },
                    },
                    {
                    type: 'category',
                    data: this.emgTime,
                    gridIndex: 1,
                    name: 'Time (s)',
                    axisLabel: {
                        interval: (index) => {
                            // Only show every 25-second label on the x-axis
                            return index % (25 * 200) === 0;
                        },
                        },
                        axisTick: {
                        alignWithLabel: true,
                        },
                    }
                ],
                yAxis: [
                    {
                        gridIndex: 0,
                        type: 'value',
                        name: 'Amplitude (V)',
                        yAxisIndex: 0,
                        scale: true,
                        splitArea: {
                            show: true
                        }
                    }, 
                    {
                        gridIndex: 1,
                        type: 'value',
                        name: 'Amplitude (V)',
                        scale: true,
                        splitArea: {
                            show: true
                        }
                    }
                ],
                series: [
                    {
                    name: 'MR',
                    type: 'line',
                    data: this.mr,
                    xAxisIndex:0,
                    yAxisIndex: 0,
                    showSymbol:false,
                    markArea: {
                        itemStyle: {
                            color: '#d0aee5',
                            borderColor: '#a942e9',  // Border color of the mark area
                            borderWidth: 2,  // Border width
                        },
                        data: markAreaData
                    }
                    /*
                    markLine: {}
                    */
                    },
                    {
                    name: 'ML',
                    type: 'line',
                    data: this.ml,
                    xAxisIndex:1,
                    yAxisIndex: 1,
                    showSymbol:false,
                    markArea: {
                        itemStyle: {
                            color: '#d0aee5',
                            borderColor: '#a942e9',  // Border color of the mark area
                            borderWidth: 2,  // Border width
                        },
                        data: markAreaData
                    }
                    /*
                    markLine: {}
                    */
                    },
                ]
                }
            
            this.emgChart.setOption(option);



        },
        generateHeatmapData(totalDurationInSeconds, events) {
            const cellsPerRow = 18;          // Number of cells in each row
            const cellDuration = 300;        // Each cell represents 5 minutes = 300 seconds (5 min * 60 s)

            // Total number of cells based on the total duration in seconds
            const totalCells = Math.ceil(totalDurationInSeconds / cellDuration);
            const numRows = Math.ceil(totalCells / cellsPerRow); // Total number of rows needed
            console.log(numRows);

            let heatmapData = [];

            // Initialize heatmap data with zeros
            for (let row = 0; row < numRows; row++) {
                for (let col = 0; col < cellsPerRow; col++) {
                    const cellIndex = row * cellsPerRow + col;

                    if (cellIndex >= totalCells) break; // Stop if we exceed the total number of cells

                    const value = 0;  // Default value
                    heatmapData.push([col, row, value]); // Note: Col (x) first, then Row (y)
                }
            }
            console.log(events)
            if(Object.keys(events).length !== 0){
                events = events.replace(/NaN/g, 'null');
                events = JSON.parse(events)
                // Now we will check the events to populate the heatmap data
                for (const eventKey in events) {
                    console.log("eventKey: ", eventKey)
                    const event = events[eventKey];
                    const start = event.start_s; // Start time of the event
                    const end = event.end_s;     // End time of the event

                    // Determine which cells the event falls into
                    for (let row = 0; row < numRows; row++) {
                        for (let col = 0; col < cellsPerRow; col++) {
                            const cellIndex = row * cellsPerRow + col;

                            if (cellIndex >= totalCells) break; // Stop if we exceed total cells

                            // Calculate the start and end times for the current cell
                            const cellStart = (col + (row * cellsPerRow)) * cellDuration; // Start time of the cell
                            const cellEnd = cellStart + cellDuration; // End time of the cell

                            // Check if the event falls within the cell's time range
                            if (start < cellEnd && end > cellStart) {
                                // Increment the value for the corresponding cell
                                heatmapData[cellIndex][2] += 1; // Increment the value at index 2 (the value field)
                            }
                        }
                    }
                }
            }

            return { "HM": heatmapData, "rows": numRows }; // Return the heatmap data and number of rows
        },
        drawECHeatMap(){
            let chartInstance = markRaw(echarts.init(document.getElementById('ec-heatmap')));
            let option;
            const minutes = [
                5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90
            ];

            let heatMapData = this.generateHeatmapData(this.emgDataLengthS, this.predictions);
            let data = heatMapData["HM"]
            console.log(heatMapData)
            let numRows = heatMapData["rows"]

            const sleepCycles = Array.from({length:numRows}, (_, i) => i + 1);

            //let data = [[0,0,0], [4, 0, 0], [2,1,0], [2,2,0], [3,1,0], [0, 1, 0], [1, 0, 0], [1,1, 0], [2, 0, 0], [3, 0, 0], [8, 8, 0], [5,4,3], [6, 2, 3], [14,4,2],[17, 0, 0], [15,1,0], [12,1,0], [7,1,0], [6,1,0], [5,1,0], [4,2,0], [4,0,0], [4,1,0], [4,3,0], [4,4,0], [0,4,0], [1,4,0], [2,4,0], [14,3,0], [15,3,0], [16,3,0]]
            //let selectedInterval = [[0,0,0]];


            option = {
                tooltip: {
                    position: 'top',
                    formatter: function (params) {
                        let fiveMinInterval = parseFloat(params.data[0])+(params.data[1]*18)
                        return `<b>Start (s)</b>: ${fiveMinInterval*60*5}<br><b>End (s)</b>: ${(fiveMinInterval*60*5)+(60*5)}`;
                    }
                },
                grid: {
                    height: '50%',
                    top: '10%'
                },
                xAxis: {
                    type: 'category',
                    name: "minutes",
                    data: minutes,
                    splitArea: {
                        show: true
                    }
                },
                yAxis: {
                    type: 'category',
                    name:"Sleep cycle", 
                    data: sleepCycles,
                    inverse: true,
                    show: true,
                    splitArea: {
                        show: true
                    }
                },
                visualMap: [{
                    type: 'continuous',
                    dimension: 2,
                    min: 0,
                    max: Object.keys(this.predictions).length == 0? 0: Object.keys(...this.predictions).length,
                    seriesIndex: 0,
                    calculable: false,
                    show: false,
                },
                {
                    dimension: 2,
                    seriesIndex : 1,
                    calculable: false,
                    show: false,
                    inRange: {
                        color: []
                    }
                }],
                series: [
                    {
                    name: 'Intervals',
                    type: 'heatmap',
                    data: data,
                    seriesIndex: 0,
                    label: {
                        show: true,
                        formatter: function (params) {
                            console.log(params)
                            if(parseInt(params.data[2])>0){
                                return params.data[2]
                            } else {
                                return ``;
                            }
                            
                        }
                    },
                    itemStyle: {
                        borderColor: '#f4d79a',
                        borderType: 'solid',
                        borderWidth: 1,
                        show:false
                    },
                    emphasis: {
                            itemStyle: {
                                shadowBlur: 10,
                                shadowColor: 'rgba(0, 0, 0, 0.5)'
                            }
                    }
                    },
                    {
                        type: 'heatmap',
                        data: this.selectedInterval,
                        seriesIndex: 1,
                        label: {
                            show: false
                        },
                        itemStyle: {
                            borderColor: 'black',
                            borderType: 'solid',
                            borderWidth: 2,
                            show:false
                        }
                    }
                ]
            };
            chartInstance.setOption(option);

            // Add a click event listener
            chartInstance.on('click', function(params) {
                console.log("clicked")
                this.selectedInterval = [];
                this.emgReceived = false;
                option.series[1].data = this.selectedInterval;
                chartInstance.setOption(option)
                console.log(params.data)
                this.selectedInterval.push(params.data)
                option.series[1].data = this.selectedInterval;
                chartInstance.setOption(option)
        
                console.log(this.selectedInterval)

                let fiveMinInterval = (params.data[0])+(params.data[1]*18)
                console.log(fiveMinInterval)
                this.tileIndex = fiveMinInterval.toFixed(2);
                this.getData(fiveMinInterval.toFixed(2));
            }.bind(this));


        }
    }
  };
  </script>