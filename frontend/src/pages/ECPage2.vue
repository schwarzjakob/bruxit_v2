<template>
    <div v-loading="!emgReceived">
        <div v-if="emgReceived">
            <button @click="changeData">Update Data</button>

            <div ref="chart" style="width: 100%; height: 400px;"></div>
        </div>
    </div>
    
</template>

<script>
import * as echarts from 'echarts';
import axios from 'axios';
//import { ref } from 'vue';
import { markRaw } from 'vue';

export default{
    name: 'ECPage2',
    data () {
        return {
            mr: [],
            ml: [],
            mrMVC: 0,
            mlMVC: 0,
            emgTime: [],
            emgReceived: false,
            rri: [],
            rriTime: [],
            rriReceived: false,
            chartInstance: null,
            chartOptions: {
                tooltip: {
                    show: true,
                    trigger: 'axis',
                    axisPointer: {
                        type: 'cross',
                        label: {
                            formatter: function(value) {
                                // Ensure that the value is formatted to two decimal places
                                return parseFloat(value.value).toFixed(2);
                            }
                        }
                    },

                    borderWidth: 1,
                    borderColor: '#ccc',
                    padding: 10,
                    textStyle: {
                    color: '#000'
                    },
                    
                    formatter: function (params) {
                        console.log("PARAMS: ", params)
                        if (params !== undefined) {  

                            let xPoint = params[0].dataIndex;
                            let yPoint = params[0].value;

                            // Format the value to 2 decimal places
                            const formattedValue = yPoint.toFixed(2);

                            // Return the tooltip HTML
                            return `                        
                                ${params[0].marker}  <b>MR</b> : ${formattedValue} mV<br>
                                <hr>
                                t: ${(xPoint/256).toFixed(2)} s<br>
                                Sampling Rate: 256 Hz<br>
                                Sleep cycle: 1<br>
                            `;

                        }
                            
                    }
                },
                xAxis: {
                    type: 'category',
                    name: 'Time (s)',
                    data: [],
                    axisLabel: {
                        formatter: (value) => {
                            // Convert to integer for the x-axis labels
                            return `${Math.floor(value)}`;
                        },
                        interval: 25*256
                    },
                },
                yAxis: {
                    type: 'value'
                },
                series: []
            }
        }
    },
    components: {

    },
    async mounted() {
        await this.getEMGData();
        //await this.getRRIData();
        console.log(this.mr)
        this.drawLineChart();
    },
    methods: {
        async getEMGData(){
            const path = `http://127.0.0.1:5000/get-emg`
            const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            };

            await axios.get(path, {headers})
                .then((res) => {
                    console.log(res.data)
                    this.mr = res.data.MR;
                    this.ml = res.data.ML;
                    this.mrMVC = res.data.MR_mvc;
                    this.mlMVC = res.data.ML_mvc;
                    this.emgTime = res.data.EMG_t;
                    this.chartOptions.xAxis.data = res.data.EMG_t;
                    this.chartOptions.series.push({
                        data: res.data.MR,
                        type: 'line',
                    })


                    this.emgReceived = true;

                })
                .catch(err=>{
                    console.log(err)
                })
        },
        async getRRIData(){
            const path = `http://127.0.0.1:5000/get-rri/`
            const headers = {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
            };

            await axios.get(path, {headers})
                .then((res) => {
                    console.log(res.data)
                    this.rri = res.data.RRI;
                    this.rriTime = res.data.RRI_t;
                })
                .catch(err=>{
                    console.log(err)
                })
        },
        drawLineChart(){
            //this.chartInstance = echarts.init(this.$refs.chart);
            this.chartInstance = markRaw(echarts.init(this.$refs.chart));
            this.chartInstance.setOption(this.chartOptions);
        },
        updateChartOptions(newOptions) {
            if (this.chartInstance) {
                this.chartInstance.setOption(newOptions, true);
            }
        },
        changeData() {
            // Update the chart options with new data
            this.updateChartOptions({
                xAxis: {
                type: 'category',
                data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                },
                yAxis: {
                type: 'category'
                },
                series: [
                {
                    data: [1200, 1400, 1300, 1600, 1700, 1500, 1400],
                    type: 'line'
                }
                ]
            });
        }
    }
}
</script>