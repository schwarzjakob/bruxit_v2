<template>
<div class="form-container">
    <el-card class="box-card">
        <template #header>
            <span><h1>Settings</h1></span>
        </template>
        <el-form ref="form" :model="form" :rules="rules" status-icon label-width="130px">
            <h2>Senors Names</h2>
            <el-form-item label="EMG Right" prop="emgRight">
                <el-input v-model="form.emgRight"></el-input>
            </el-form-item>
            
            <el-form-item label="EMG Left" prop="emgLeft">
                <el-input v-model="form.emgLeft"></el-input>
            </el-form-item>

            <el-form-item label="ECG" prop="ecg">
                <el-input v-model="form.ecg"></el-input>
            </el-form-item>

            <h2>Model File Name</h2>
            <el-form-item label="Model File Name" prop="modelFileName">
                <el-input v-model="form.modelFileName"></el-input>
            </el-form-item>
            <h2>Data Paths</h2>
            <el-form-item label="Original Data" prop="originalDataPath">
                <el-input v-model="form.originalDataPath"></el-input>
            </el-form-item>

            <el-form-item label="Downsampled Data" prop="downsampledDataPath">
                <el-input v-model="form.downsampledDataPath"></el-input>
            </el-form-item>

            <el-form-item label="Model" prop="modelPath">
                <el-input v-model="form.modelPath"></el-input>
            </el-form-item>

            <h2>Sampling Rates (Hz)</h2>
            <el-form-item label="Original" prop="originalSamplingRate">
                <el-input-number v-model="form.originalSamplingRate" :disabled="true"></el-input-number>
            </el-form-item>

            <el-form-item label="Minimum" prop="minimumSamplingRate">
            <el-input-number v-model="form.minimumSamplingRate" :disabled="true"></el-input-number>
            </el-form-item>

            <!-- Save -->
            <el-form-item>
                <el-button type="primary" @click="saveSettings">Save</el-button>
            </el-form-item>
        </el-form>
    </el-card>
</div>
</template>

<script>
import { ElMessage } from 'element-plus'
import axios from 'axios';

export default{
    name: "SettingsPage",
    async beforeMount() {
            await this.getSettings();
        },
    data() {
        return {
        form: {
            emgRight: '',
            emgLeft: '',
            ecg: '',
            modelFileName: '',
            originalDataPath: '',
            downsampledDataPath: '',
            modelPath: '',
            originalSamplingRate: 2000,
            minimumSamplingRate: 200
        },
        rules: {
            emgRight: [{ required: true, message: 'Please enter EMG right sensor', trigger: 'blur' }],
            emgLeft: [{ required: true, message: 'Please enter EMG left sensor', trigger: 'blur' }],
            ecg: [{ required: true, message: 'Please enter ECG sensor', trigger: 'blur' }],
            modelFileName: [{ required: true, message: 'Please enter model file name', trigger: 'blur' }],
            originalDataPath: [{ required: true, message: 'Please enter original data path', trigger: 'blur' }],
            downsampledDataPath: [{ required: true, message: 'Please enter downsampled data path', trigger: 'blur' }],
            modelPath: [{ required: true, message: 'Please enter model data path', trigger: 'blur' }]
        }
        };
    },
    methods: {
        async getSettings(){
            const path = `http://127.0.0.1:5000/settings`
            const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            };

            await axios.get(path, {headers})
                .then((res) => {
                    console.log("ciao")
                    console.log(res.data)

                    if(Object.keys(res.data).length > 0){
                        this.form.emgRight = res.data.emgRight;
                        this.form.emgLeft = res.data.emgLeft;
                        this.form.ecg = res.data.ecg;
                        this.form.modelFileName = res.data.modelFileName;
                        this.form.originalDataPath = res.data.originalDataPath;
                        this.form.downsampledDataPath = res.data.downsampledDataPath;
                        this.form.modelPath = res.data.modelPath;
                        this.form.originalSamplingRate = res.data.originalSamplingRate;
                        this.form.minimumSamplingRate = res.data.minimumSamplingRate;
                    }
                })
                .catch(err=>{
                    console.log(err)
                })
        },
        async saveSettings() {
            this.$refs.form.validate(async (valid) => {
                if (valid) {
                    const path = `http://127.0.0.1:5000/settings`
                    const headers = {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    };
                    let payload = {
                        emgRight: this.form.emgRight,
                        emgLeft: this.form.emgLeft,
                        ecg: this.form.ecg,
                        modelFileName: this.form.modelFileName,
                        originalDataPath: this.form.originalDataPath,
                        downsampledDataPath: this.form.downsampledDataPath,
                        modelPath: this.form.modelPath,
                        originalSamplingRate: this.form.originalSamplingRate,
                        minimumSamplingRate: this.form.minimumSamplingRate,
                    };

                    try {
                        // Post the data and wait for the response
                        await axios.post(path, payload, { headers });
                        console.log('Form Submitted:', this.form);
                        ElMessage({
                            message: 'Settings saved successfully.',
                            type: 'success',
                        });
                    } catch (err) {
                        console.log(err);
                    }
                } else {
                    ElMessage.error('Unable to save settings, please fill in all the input fields.');
                    console.log('Form validation failed');
                    return false;
                }
            });
        }
    }
}
</script>

<style scoped>
.form-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
}

.box-card {
  width: 600px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-radius: 8px;
}

.el-form-item {
  margin-bottom: 20px;
}

</style>