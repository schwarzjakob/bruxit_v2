<template>
    <el-row>
        <el-col :offset="4">
            <el-tag :type="userTypeTagType" size="large">
                {{ userType.charAt(0).toUpperCase() + userType.slice(1) }}
            </el-tag>
        </el-col>
    </el-row>
    <el-row justify="center">
        <h1>Patient Data</h1>
    </el-row>

    <el-row justify="center" style="margin-bottom: 100px">
        <el-col :span="10">
            <PipelineStepper :step="0" />
        </el-col>
    </el-row>

    <el-row justify="center">
        <h2>Choose the night of your choice:</h2>
    </el-row>

    <el-row justify="center">
        <el-col :span="12">
            <el-collapse v-model="activePanels">
                <el-collapse-item v-for="(weeks, patientId) in patientsData" :key="patientId">
                    <template #title>
                        <el-tag size="large">
                            <b>Patient {{ patientId }}</b>
                        </el-tag>
                    </template>

                    <el-collapse>
                        <el-collapse-item
                            v-for="(files, weekId) in weeks"
                            :key="weekId"
                            :title="'Week ' + weekId"
                        >
                            <el-radio-group v-model="selectedFile" size="large">
                                <el-tooltip
                                    v-for="file in files"
                                    :key="file.file_name"
                                    class="item"
                                    effect="dark"
                                    :content="getTooltipContent(file)"
                                    placement="top"
                                >
                                    <el-button
                                        style="margin-left: 5px;"
                                        @click="storeSelectedPatientFile(patientId, weekId, file.file_name, file.size_gb)"
                                    >
                                        {{file.file_name}}
                                    </el-button>
                                </el-tooltip>
                            </el-radio-group>
                        </el-collapse-item>
                    </el-collapse>
                </el-collapse-item>
            </el-collapse>
        </el-col>
    </el-row>
</template>

<script>
import PipelineStepper from '../components/PipelineStepper.vue'
import axios from 'axios';
import {ref} from 'vue'


export default{
    name: 'PatientData',
    components: {
        PipelineStepper
    },
    data () {
        return {
            userType: '',
            activePanels: [],
            selectedFile: ref(''),
            patientsData: {},
            userTypeTagType: ""
        }
    },
    async mounted(){
        await this.getUserType();
        await this.getPatientsData();
    },
    methods: {
        async getUserType(){
            this.userType = this.$store.state.userType;

            if(this.$store.state.userType === "advanced"){
                this.userTypeTagType = "success"
            } 
            if(this.$store.state.userType === "basic"){
                this.userTypeTagType = "warning"
            }
        },
        async getPatientsData(){
            const path = `http://127.0.0.1:5000/patients-data`
            const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            };

            await axios.get(path, {headers})
                .then((res) => {
                    console.log(res.data)
                    this.patientsData = res.data;

                })
                .catch(err=>{
                    console.log(err)
                })
        },
        storeSelectedPatientFile(patientId, weekId, file_name, file_size){
            console.log("Patient " + patientId + ",week " + weekId + ", file_name: " + file_name + " size_gb: " + file_size )
            console.log(this.selectedFile)
            this.$store.commit('setPatientId', patientId);
            this.$store.commit('setWeekId', String(weekId));
            this.$store.commit('setFile', String(file_name));
            this.$store.commit('setFileSize', parseFloat(file_size))
            this.$router.push('/ssd');
        },
        getTooltipContent(file) {
            return `Size: ${file.size_gb} GB`;
        }
    }
}

</script>