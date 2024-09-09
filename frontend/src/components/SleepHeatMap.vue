<template>
    <div style="text-align: center;">
        <div style="display: inline-block;">
            <router-link :to="'/patient-data/'">
                <el-button type="primary" plain><el-icon class="el-icon--left"><ArrowLeft /></el-icon> Patients Data</el-button>
            </router-link>
        </div>
        <div v-if="!error" style="display: inline-block; padding-left: 12%; padding-right: 12%;">
            <el-button @click="toggleEditMode" v-if="!isEditMode">Edit intervals of interest</el-button>
            <el-popconfirm
            title="Save the selected intervals of interest?"
            confirm-button-text="Yes"
            cancel-button-text="No"
            @confirm="toggleEditMode"
            @cancel="exitEditMode"
            width="350">
                <template #reference>
                    <el-button v-if="isEditMode"> Save</el-button>
                </template>
            </el-popconfirm>
        </div>
        <div style="display: inline-block;">
            <router-link :to="'/events-classification/'">
                <el-button v-if="!error" type="primary" plain :disabled="isEditMode">
                    Events Classification<el-icon class="el-icon--right"><ArrowRight /></el-icon>
                </el-button>
            </router-link>
        </div>
    </div>
    <div v-if="selectedPosted">
        <el-alert title="Selected intervals selected successfully." type="success" center show-icon /> 
    </div>

    <el-dialog v-model="selectedPosted" title="Continue with selected intervals?" width="30%" center align-center="true" draggable="true">
        <span>
            Do you want to continue to the Events Classification Page?
        </span>
        <template #footer>
        <span class="dialog-footer">
            <el-button @click="selectAgain">No</el-button>
            <el-button type="primary" @click="continueToEventsClassificationPage">
                Yes
            </el-button>
        </span>
        </template>
  </el-dialog>

  <el-row :align="middle">
        <el-col v-if="error" :span="24">
            <el-result
                icon="error"
                title="Error"
            >
                <template #extra>
                    <p>{{ getSubtitle() }}</p>
                    <router-link :to="'/patient-data/'">
                        <el-button type="primary" plain>Back</el-button>
                    </router-link>
                </template>
            </el-result>
        </el-col>
        <el-col v-if="!error" :span="24" v-loading="loading" element-loading-text="The dataset is loading...it might take a couple of minutes.">
            <div id="chart-container" style="position: relative; height: 100vh; overflow: hidden;"></div>
        </el-col>
    </el-row>
</template>

<script>
import * as echarts from 'echarts';
import axios from 'axios';
import { ref } from 'vue';
import { ElMessage } from 'element-plus';
import SleepHeatMapLegend from './SleepHeatMapLegend.vue';

export default {
  name: 'SleepHeatMap',
  data () {
    return {
      dataReceived: false,
      selectedOnDb: [],
      loading: ref(true),
      isEditMode: false,
      error: false,
      clicked: [],
      firstEnteredEditMode: false,
      selectedPosted: false,
      noSelectedError: false,
      patientData: []
    }
  },
  components: {
    SleepHeatMapLegend
  },
  async mounted() {
    await this.getPatientData();
    await this.getCurrentlySelected();
    this.loading = ref(false);
    this.drawTreatHeatMap();
  },
  methods: {
    open() {
        ElMessage('Please choose the cell for which you want to modify the label.')
    },
    getSubtitle(){
        return "No dataset found for user " + this.$store.state.patientId + " on night " + this.$store.state.nightId + " of week " + this.$store.state.week + "."
    },
    arrayEquals(a, b){
        return a.length === b.length && a.every((item,idx) => item === b[idx])
    },
    getMaxSD(arr1, arr2, prop) {
        var max1;
        var max2;
        if(arr1.length === 0){
            max1 = 0;
        }
        if(arr2.length === 0){
            max2 = 0;
        }
        if(arr1.length > 0 || arr2.length >0){
            for (var i=0 ; i<arr1.length ; i++) {
                if (max1 == null || parseInt(arr1[i][prop]) > parseInt(max1[prop]))
                    max1 = arr1[i];
            }

            for (var i=0 ; i<arr2.length ; i++) {
                if (max2 == null || parseInt(arr2[i][prop]) > parseInt(max2[prop]))
                    max2 = arr2[i];
            }


            return Math.max(max1.SD, max2.SD);
        }

        
    },
    getMinSD(arr1, arr2, prop) {
        var min1;
        var min2;
        if(arr1.length === 0 ){
            min1 = 0
        }
        if(arr2.length === 0){
            min2 = 0
        }
        if(arr1.length > 0 || arr2.length >0){
           for (var i=0 ; i<arr1.length ; i++) {
            if (min1 == null || parseInt(arr1[i][prop]) < parseInt(min1[prop]))
                min1 = arr1[i];
            }

            for (var i=0 ; i<arr2.length ; i++) {
            if (min2 == null || parseInt(arr2[i][prop]) < parseInt(min2[prop]))
                min2 = arr2[i];
            }

            return Math.min(min1.SD, min2.SD)
        }

        
    },
    selectAgain(){
        this.$router.go();
    },
    continueToEventsClassificationPage(){
        if(this.selectedPosted){
            this.$router.push('/events-classification/');
        } else {
            this.$router.go();
            this.noSelectedError = true;
        }
    },

    toggleEditMode() {
      this.isEditMode = !this.isEditMode;
      this.firstEnteredEditMode = true;
      if(!this.isEditMode){
        const path = `http://127.0.0.1:5000/selected-sleep-phases/${this.$store.state.patientId}/${this.$store.state.week}/${this.$store.state.nightId}/`
        const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
        };

        let payload = [];

        for(let i=0; i<this.clicked.length; i++){
            payload.push({
                "x": this.clicked[i][0],
                "y": this.clicked[i][1],
            })
        }
        
        axios.post(path, payload, {headers})
            .then((res) => {
                this.clicked = [];
                this.selectedPosted = true;
                //this.$router.push('/events-classification/');
                
                this.$store.commit('clearLabels');
                this.$store.commit('getNightImg', '');
                this.$store.commit('getWeekImg', '');
                this.$store.commit('setPredFinish', false);
                this.$store.commit('setEventNo', 1);
                console.log('repredict')

            })
            .catch(err=>{
                console.log(err)
            })

      }

    },
    async getCurrentlySelected(){
        const path = `http://127.0.0.1:5000/selected-sleep-phases/${this.$store.state.patientId}/${this.$store.state.week}/${this.$store.state.nightId}/`
        const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
        };

        await axios.get(path, {headers})
            .then((res) => {
                console.log("DATA RECEIVED!")
                console.log(res.data);
                this.clicked = res.data;
                this.dataReceived = true;
            })
            .catch(err=>{
                console.log(err)
            })
    },
    exitEditMode(){
        this.isEditMode = !this.isEditMode;
        this.clicked = [];
        this.$router.go();
    },

    async getPatientData(){
        const path = `http://127.0.0.1:5000/ssd/${this.$store.state.patientId}/${this.$store.state.week}/${this.$store.state.nightId}/${this.$store.state.recorder}/`
        const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
        };

        await axios.get(path, {headers})
            .then((res) => {
                console.log(res.data)
                this.patientData = res.data;

            })
            .catch(err=>{
                console.log(err)
                this.error = true;
            })
    },

    drawTreatHeatMap(){
        var dom = document.getElementById("chart-container");
        var myChart = echarts.init(dom, null, {
            renderer: "sgv",
            useDirtyRect: false
        });

        var option;
        var maxY = 0;
        var hours = [];
        var minutes = [5, 10 , 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90];
        var remDataJson = []
        var nremDataJson = []

        for (var i=0; i < this.patientData.length; i++) {
            if(this.patientData[i]['y'] > maxY){
                maxY = this.patientData[i]['y']
            }
            if(this.patientData[i]['stage'] === 'rem'){
                remDataJson.push(this.patientData[i]);
            }
            else {
                nremDataJson.push(this.patientData[i]);
            }
        }

        for(var i=1; i<=(maxY+1); i+=1){
            hours.push(i);
        }

        var remData = remDataJson.map(function (item) {
            return [item['x'], item['y'], Math.round(item['SD']), item['stage'], item['LF_HF']];
        });

        var nremData = nremDataJson.map(function (item) {
            return [item['x'], item['y'], Math.round(item['SD']), item['stage'], item['LF_HF']];
        });

        var callback = (args) => {
            return args.seriesName + "<br />" +args.marker  + args.value[4].toFixed(2) + '±' + args.value[2]
        }

        option = {
            tooltip: {
                position: 'top',
                formatter: callback
            },
            animation: false,
            grid: {
                height: '50%',
                top: '10%'
            },
            xAxis: {
                axisLabel: {
                    padding: [0, -60, 0, 0]
                },
                position: 'right',
                type: 'category',
                name: 'min',
                data: minutes,
                splitArea: {
                    show: true
                },
            },
            yAxis: {
                axisLabel: {
                    //why padding not working for 'top'?
                    padding: [-60, 0, 0, 0],
                },
                type: 'category',
                data: hours,
                name: 'Sleep cycles',
                splitArea: {
                    show: true
                },
                inverse: true
            },
            visualMap: [{
                min: this.getMinSD(remDataJson, nremDataJson, "SD"),
                max: this.getMaxSD(remDataJson, nremDataJson, "SD"),
                text: ["high", "low"],
                formatter: 'Level of uncertainity: {value}',
                dimension: 2,
                inRange : {
                    color: ['#1919ff', '#CCCCFF'] //From bigger to smaller value ->
                },
                seriesIndex : 0,
                calculable: false,
                orient: 'horizontal',
                left: 'center',
                bottom: '30%',
            }, {
                min: this.getMinSD(nremDataJson, remDataJson, "SD"),
                max: this.getMaxSD(nremDataJson, remDataJson, "SD"),
                text: ["high", "low"],
                formatter: 'Level of uncertainity: {value}',
                dimension: 2,
                inRange : {
                    color: ['#999999', '#eeeeee'] //From bigger to smaller value ->
                },
                seriesIndex : 1,
                calculable: false,
                orient: 'horizontal',
                left: 'center',
                bottom: '24%',
            }, {
                dimension: 2,
                seriesIndex : 2,
                calculable: false,
                show: false,
                inRange: {
                    color: []
                }
            }],
            series: [{
                name: '<b>LF/HF ratio ± Standard Deviation (SD)</b>',
                type: 'heatmap',
                data: remData,
                label: {
                    show: true,
                    formatter: (param) => {
                        if (JSON.stringify(this.clicked).includes(JSON.stringify(param.data))){
                            return 'REM *'

                        } else {
                            return 'REM'
                        }

                    }
                },
                emphasis: {
                    itemStyle: {
                        shadowBlur: 10,
                        shadowColor: 'rgba(0, 0, 0, 0.5)',
                        borderColor: 'black',
                        borderWidth: 3
                    }
                }
            }, {
                name: '<b>LF/HF ratio ± Standard Deviation (SD)</b>',
                type: 'heatmap',
                data: nremData,
                label: {
                    show: true,
                    formatter: (param) => {
                        if (JSON.stringify(this.clicked).includes(JSON.stringify(param.data))){
                            return '*'

                        } else {
                            return ''
                        }
                    }
                },
                emphasis: {
                    itemStyle: {
                        shadowBlur: 10,
                        shadowColor: 'rgba(0, 0, 0, 0.5)',
                        borderColor: 'black',
                        borderWidth: 3
                    }
                }
            }, {
                name: '<b>LF/HF ratio ± Standard Deviation (SD)</b>',
                type: 'heatmap',
                data: this.clicked,
                itemStyle: {
                    borderColor: 'black',
                    borderType: 'dashed',
                    borderWidth: 2
                }
            
            }]
        };


        myChart.on('click', (params) => {
            console.log('Tile clicked:', params);
        
        if(this.isEditMode){
            if(this.firstEnteredEditMode){
            console.log("FIRST")
            let remData = option.series[0].data
            if(!this.dataReceived || this.clicked.length === 0){
                console.log("Data not received")
                for(const key in remData){
                    this.clicked.push(remData[key])
                    myChart.dispatchAction({
                        type: 'highlight',
                        seriesIndex: 0,
                        dataIndex: key
                    })
                }
                myChart.dispatchAction({
                    type: 'highlight',
                    seriesIndex: params.seriesIndex,
                    dataIndex: params.dataIndex
                })
            } else {
                for(let i=0; i<this.clicked.length; i++){
                    if (this.clicked[i][3] === 'rem'){
                        console.log("CLICKED REM FIRST ENTERED")

                        let dataSeries = option.series[0].data;
                        for(const key in dataSeries){
                            if (JSON.stringify(dataSeries[key]) === JSON.stringify(this.clicked[i])){
                                myChart.dispatchAction({
                                type: 'highlight',
                                seriesIndex: 0,
                                dataIndex: key
                            })

                            } 
                        }
                    } else {
                        console.log("CLICKED NREM FIRST ENTERED")
                        let dataSeries = option.series[1].data;
                        for(const key in dataSeries){
                            if (JSON.stringify(dataSeries[key]) === JSON.stringify(this.clicked[i])){
                                myChart.dispatchAction({
                                type: 'highlight',
                                seriesIndex: 1,
                                dataIndex: key
                            })

                            } 
                        }
                    }
                    
                }

            }
            
            this.firstEnteredEditMode = !this.firstEnteredEditMode;
            } else {
            if(JSON.stringify(this.clicked).includes(JSON.stringify(params.data))){
                console.log("includes")
                this.clicked = this.clicked.filter(item => !this.arrayEquals(item, params.data))
                console.log(params.seriesIndex)
                console.log(params.dataIndex)
                myChart.dispatchAction({
                    type: 'downplay',
                    seriesIndex: params.seriesIndex,
                    dataIndex: params.dataIndex
                })

            } else {
                console.log("ELSE")
                this.clicked.push(params.data)
                myChart.dispatchAction({
                    type: 'highlight',
                    seriesIndex: params.seriesIndex,
                    dataIndex: params.dataIndex
                })
            }

            }
        }
        });

            if (option && typeof option === "object") {
            myChart.setOption(option);
        }

        window.addEventListener("resize", myChart.resize);
    }


}
}
</script>

<style scoped>
.buttons-container {
  position: absolute;
  top: 175px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 10px;
}
</style>
