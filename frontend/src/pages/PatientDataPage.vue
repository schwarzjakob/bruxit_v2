<template>
    <el-row style="margin-top: 10px;">
        <el-col :span="1" :offset="4"><UserTag /></el-col>
        <el-col :span="13" :offset="1"><PipelineStepper :step="1" /></el-col>
    </el-row>

    <el-row justify="center">
        <h2>Choose the patient's file of your choice:</h2>
    </el-row>

    <el-row justify="center">
        <el-col :span="12">
            <el-collapse v-model="activePanels" v-loading="loading" element-loading-text="Downsampling dataset...">
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
import UserTag from '../components/UserTag.vue';

export default{
    name: 'PatientData',
    components: {
        PipelineStepper,
        UserTag
    },
    data () {
        return {
            activePanels: [],
            selectedFile: ref(''),
            patientsData: {},
            loading: false
        }
    },
    async mounted(){
        await this.getPatientsData();
    },
    methods: {
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
        async downsampleSelectedPatientData(patientId, weekId, file_name){
            this.loading = true;
            const path = `http://127.0.0.1:5000/downsample-data/${patientId}/${weekId}/${file_name}`
            const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            };

            await axios.get(path, {headers})
                .then(() => {
                    this.loading = false;
                    console.log("Data downsampled")
                })
                .catch(err=>{
                    console.log(err)
                })
        },
        async storeSelectedPatientFile(patientId, weekId, file_name, file_size){
            console.log("Patient " + patientId + ",week " + weekId + ", file_name: " + file_name + " size_gb: " + file_size )
            console.log(this.selectedFile)
            this.$store.commit('setPatientId', patientId);
            this.$store.commit('setWeekId', String(weekId));
            this.$store.commit('setFile', String(file_name));
            this.$store.commit('setFileSize', parseFloat(file_size))
            await this.downsampleSelectedPatientData(patientId, weekId, file_name)
            this.$router.push('/ec-def');
        },
        getTooltipContent(file) {
            return `Size: ${file.size_gb} GB`;
        }
    }
}

</script>