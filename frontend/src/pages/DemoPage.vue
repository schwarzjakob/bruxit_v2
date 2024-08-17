<template>
<!--HEADER ROW-->
<el-row style="margin-top: 10px;">
    <el-col :span="2"><el-button type="primary"> <el-icon> <ArrowLeft /> </el-icon> Sleep Stage Detection</el-button></el-col>
    <el-col :span="1" :offset="2"><el-tag type="success">Advanced</el-tag></el-col>
    <el-col :span="13" :offset="1"><PipelineStepper :step="3"/></el-col>
    <el-col :span="2" :offset="1"><el-button type="primary"> Monitoring Dashboards  <el-icon> <ArrowRight /> </el-icon></el-button></el-col>
</el-row>

<!--IMAGE ROW-->
<el-row justify="center">
    <h3>Signal and predicted events: Patient 2, w1, night 0204451</h3>
    <el-button type="info" @click="toggleImage" style="margin-left: 20px; margin-top: 10px" plain>
      {{ isImageVisible ? 'Hide' : 'Show' }} Image
    </el-button>
</el-row>
<el-row justify="center">
    <el-image v-if="isImageVisible" :src="nightPredImg" style="max-width: 1000px"/>
</el-row>

<!--EVENTS CARDS AND PLOTS ROW-->
<el-row>
    <!--EVENTS CARDS-->
    <el-col :span="6">
        <el-card>
            <h2>Events predicted</h2>
            <p><u>Cycle 2</u></p>
        </el-card>
    </el-col>
    <!--PLOTS-->
    <el-col :span="16">
        <el-row>
            <el-col :offset="17">
                <el-button-group>
                    <el-button :plain="true">
                        Edit Mode
                    </el-button>
                    <el-button :plain="true">
                        Zoom
                    </el-button>
                </el-button-group>
            </el-col>
        </el-row>
        <el-row style="margin-bottom: 20px;"> 
            <!--CHART-->
            <div style="display: flex; flex-direction: column; width: 100%; min-height: 100vh; overflow-y: auto;">
                <div ref="chart" style="width: 100%; height: 650px"></div>
            </div>
        </el-row>
        <!-- <el-row style="background-color: green">PLOT 2</el-row>-->
    </el-col>
    <!--SIGNALS SELECTION-->
    <el-col :span="2" style="margin-top: 50px">
        SELECT SIGNALS
    </el-col>
</el-row>


</template>

<script>
import { ArrowLeft, ArrowRight} from '@element-plus/icons-vue'
import PipelineStepper from '../components/PipelineStepper.vue'
import img from '../../../backend/src/data/p1_wk1/1022102.png'
//import { ref } from 'vue'
import * as echarts from 'echarts';
import csv from '../assets/1022102cFnorm_rms_5_min_256Hz.csv';
//import { PriceTag } from '@element-plus/icons-vue'

export default {
    name: 'DemoPage',
    data () {
        return{
            nightPredImg: img,
            isImageVisible: true,
            MR: [],
            ML: [],
            ECG: [],
            timeAxis: [],
            chart : [],
        }
    },
    components: {
        ArrowLeft,
        ArrowRight,
        PipelineStepper
    },
    async mounted() {
      await this.processData();
      await this.initializeChart();
    },
    methods: {
        async processData(){
            console.log("PROCESS DATA")
            try {
            //console.log("CSV Data:", csv);
    
            // First row is the header
            const header = csv[0];
            const mrIndex = header.indexOf('MR'); // Find the index of the 'MR' column
            const mlIndex = header.indexOf('ML'); // Find the index of the 'MR' column
            const ecgIndex = header.indexOf('ECG'); // Find the index of the 'MR' column


            if (mrIndex === -1 || mrIndex === -1 || mrIndex === -1) {
                throw new Error('Column not found in header');
            }
    
            // Remove empty rows
            const filteredRows = csv.slice(1).filter(row => row.length > 1);
    
            // Extract MR
            this.MR = filteredRows.map((row) => {
                let value = row[mrIndex];
    
                if (typeof value !== 'undefined' && value !== null) {
                value = parseFloat(value.trim()); // Clean and parse the value
                } else {
                value = NaN;
                }
                if (isNaN(value)) {
                    return null;
                }
                return value;
            }).filter(value => value !== null);

            this.ML = filteredRows.map((row) => {
                let value = row[mlIndex];
    
                if (typeof value !== 'undefined' && value !== null) {
                value = parseFloat(value.trim()); // Clean and parse the value
                } else {
                value = NaN;
                }
                if (isNaN(value)) {
                    return null;
                }
                return value;
            }).filter(value => value !== null);

            this.ECG = filteredRows.map((row) => {
                let value = row[ecgIndex];
    
                if (typeof value !== 'undefined' && value !== null) {
                value = parseFloat(value.trim()); // Clean and parse the value
                } else {
                value = NaN;
                }
                if (isNaN(value)) {
                    return null;
                }
                return value;
            }).filter(value => value !== null);
    
            // Check if there are any valid data points
            if (this.MR.length === 0 || this.ML.length === 0 || this.ECG.length === 0) {
                throw new Error('No valid data found');
            }
    
            // Create time values for the x-axis based on index
            this.timeAxis = this.MR.map((_, index) => (index / 256).toFixed(2)); // 256 samples per second
            } catch (error) {
                console.error('Error processing data:', error);
            }
        },

        async initializeChart(){
            this.chart = echarts.init(this.$refs.chart);
            const option = {
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
                legend: {
                    bottom: 10,
                    left: 'center',
                    data: ['MR', 'ML', 'ECG']
                },
                grid: [
                { left: '10%', right: '10%', top: '5%', height: '25%' },  // MR
                { left: '10%', right: '10%', top: '38%', height: '25%' }, // ML
                { left: '10%', right: '10%', top: '72%', height: '18%' }  // ECG
                ],
                xAxis: [
                {
                    gridIndex: 0,
                    type: 'category',
                    name: 'Time (s)',
                    data: this.timeAxis,
                    /*
                    axisLabel: {
                        formatter: '{value}s',
                        interval: 25*256
                    },
                    */
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
                },
                {
                    gridIndex: 2,
                    type: 'category',
                    name: 'Time (s)',
                    data: this.timeAxis,
                    axisLabel: {
                        formatter: '{value}s',
                        interval: 25*256
                    },
                }
                ],
                yAxis: [
                {
                    gridIndex: 0,
                    type: 'value',
                    name: 'Amplitude (mV)',
                    scale: true,
                    splitArea: {
                        show: true
                    },
                },
                {
                    gridIndex: 1,
                    type: 'value',
                    name: 'Amplitude (mV)',
                    scale: true,
                    splitArea: {
                        show: true
                    },
                },
                {
                    gridIndex: 2,
                    type: 'value',
                    name: 'bpm',
                    scale: true,
                    splitArea: {
                        show: true
                    },
                }
                ],
                series: [
                {
                    name: 'MR',
                    type: 'line',
                    xAxisIndex: 0,
                    yAxisIndex: 0,
                    data: this.MR,
                    showSymbol: false,
                    smooth: true,
                },
                {
                    name: 'ML',
                    type: 'line',
                    xAxisIndex: 1,
                    yAxisIndex: 1,
                    data: this.ML,
                    showSymbol: false,
                    smooth: true,
                },
                {
                    name: 'ECG',
                    type: 'line',
                    xAxisIndex: 2,
                    yAxisIndex: 2,
                    data: this.ECG,
                    lineStyle: {
                        width: 1, // Make the line thinner
                        //type: 'dashed' // Optional: dashed line to differentiate the trend
                    },
                    showSymbol: false,
                    smooth: true,
                }
                ]
            };

            this.chart.setOption(option);

            this.chart.on('brushSelected', this.onBrushSelected);
        },
        toggleImage() {
            this.isImageVisible = !this.isImageVisible; // Toggle the visibility
        },
        
        
    },
}
</script>