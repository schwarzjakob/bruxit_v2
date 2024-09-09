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
    <el-row justify="center" style="margin-bottom: 100px">
        <el-col :span="10">
            <PipelineStepper :step="1" />
        </el-col>
    </el-row>
    
<el-row justify="center"><h1>Sleep stage Detection Page</h1></el-row>
<el-row justify="center"> <h3>Patient {{ this.$store.state.patientId }}, Week {{ this.$store.state.weekId }}, file {{ this.$store.state.file }}, size {{ this.$store.state.fileSize }} GB</h3></el-row>

<SSDHeatMap />

</template>

<script>
import SSDHeatMap from '../components/SSDHeatMap.vue'

export default{
    name: 'SleepStageDetection',
    mounted(){
        console.log(this.$store.state.patientId)
        console.log(this.$store.state.weekId)
        console.log(this.$store.state.file)
        console.log(this.$store.state.fileSize)
    },
    components: {
        SSDHeatMap
    }
}
</script>