<template>
    <el-row>
        <el-col :span="2" :offset="3">
            <router-link :to="'/patient-data/'">
                <el-button type="primary" plain><el-icon class="el-icon--left"><ArrowLeft /></el-icon> Patients Data</el-button>
            </router-link>
        </el-col>
        <el-col :span="2" :offset="14">
            <router-link :to="'/ec-def/'">
                <el-button type="primary" plain> Events Classification <el-icon class="el-icon--right"><ArrowRight /></el-icon></el-button>
            </router-link>
        </el-col>
    </el-row>
    <el-row justify="center" style="margin-bottom: 20px">
        <el-col :span="10">
            <PipelineStepper :step="1" />
        </el-col>
    </el-row>
    
<el-row>
    <el-col  :span="17" style="text-align: center">
        <h1>Patient {{ this.$store.state.patientId }}, Week {{ this.$store.state.weekId }}, file {{ this.$store.state.file }}, size {{ this.$store.state.fileSize }} GB</h1>
    </el-col>
    <el-col :span="4"></el-col>
</el-row>

<el-row>
    <el-col :span="17">
        <SSDHeatMap />
    </el-col>
    <el-col :span="4" style="margin-top: 95px">
        <SleepHeatMapLegend />
    </el-col>
</el-row>
</template>

<script>
import SSDHeatMap from '../components/SSDHeatMap.vue'
import PipelineStepper from '../components/PipelineStepper.vue'
import SleepHeatMapLegend from '../components/SleepHeatMapLegend.vue';


export default{
    name: 'SleepStageDetection',
    mounted(){
        console.log(this.$store.state.patientId)
        console.log(this.$store.state.weekId)
        console.log(this.$store.state.file)
        console.log(this.$store.state.fileSize)
    },
    components: {
        SSDHeatMap,
        PipelineStepper,
        SleepHeatMapLegend
    }
}
</script>