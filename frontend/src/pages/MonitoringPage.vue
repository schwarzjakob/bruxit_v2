<template>
    <el-row style="margin-top: 10px;">
    <el-col :span="2"><router-link :to="'/ec-def/'"><el-button type="primary"> <el-icon> <ArrowLeft /> </el-icon> Sleep Stage Detection</el-button></router-link></el-col>
        <el-col :span="1" :offset="2"><el-tag type="success" size="large">Advanced</el-tag></el-col>
        <el-col :span="13" :offset="1"><PipelineStepper :step="2" /></el-col>
    </el-row>
<h1>Monitoring</h1>

<el-button @click="downloadEventsCsv">Download Events Report</el-button>
<div class="dashboard">
    <h1>XGBoost Model Dashboard</h1>
    
    <div v-if="modelSummary">
      <h2>Model Summary</h2>
      <pre>{{ modelSummary }}</pre>
    </div>

    <div v-if="featureImportance.length > 0">
      <h2>Feature Importance</h2>
      <el-table :data="featureImportance" stripe style="width: 100%">
        <el-table-column prop="feature" label="Feature" width="180"></el-table-column>
        <el-table-column prop="importance" label="Importance"></el-table-column>
      </el-table>
    </div>
</div>

</template>

<script>
import PipelineStepper from '../components/PipelineStepper.vue'
import axios from 'axios';

export default {
    name: "MonitoringPage",
    components: {
        PipelineStepper
    },
    data () {
        return {
            modelSummary: null,
            featureImportance: [],
        }
    },
    mounted () {
        this.fetchModelSummary();
        this.fetchFeatureImportance();
    },
    methods: {
        // Fetch model summary from Flask backend
        async fetchModelSummary() {
            const path = `http://127.0.0.1:5000/model-summary`
            const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            };

            await axios.get(path, {headers})
                .then((res) => {
                    this.modelSummary = res.data;

                })
                .catch(err=>{
                    console.error('Error fetching model summary:', err);
                })
        },

        // Fetch feature importance from Flask backend
        async fetchFeatureImportance() {
            const path = `http://127.0.0.1:5000/model-feature-importance`
            const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            };

            await axios.get(path, {headers})
                .then((res) => {
                    this.featureImportance = res.data.map(item => {
                        return { feature: item[0], importance: item[1] };
                    });

                })
                .catch(err=>{
                    console.error('Error fetching feature importance:', err);
                })
        },
        async downloadEventsCsv(){
            try {
                // Make an axios GET request to the Flask backend to get the CSV file
                const response = await axios({
                url: 'http://127.0.0.1:5000/download-events-csv', // URL to Flask backend
                method: 'GET',
                responseType: 'blob' // Important to handle binary response (CSV)
                });

                // Create a link element, use the URL.createObjectURL for the response
                const url = window.URL.createObjectURL(new Blob([response.data]));
                const link = document.createElement('a');
                link.href = url;
                link.setAttribute('download', 'confirmed_events.xlsx'); // Set the download filename
                document.body.appendChild(link);
                link.click();

                // Clean up and remove the link after download
                link.remove();
            } catch (error) {
                console.error('Error downloading the file:', error);
            }

        }
    }
}
</script>