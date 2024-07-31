import { createStore } from 'vuex';
import VuexPersistence from 'vuex-persist';
import localForage from 'localforage';
import {clone} from 'pouchdb-utils';

const vuexLocal = new VuexPersistence({
  storage: localForage,
  asyncStorage: true,
  reducer: (state) => clone(state),
});


const store = createStore({
  state () {
    return {
      patientId: 1,
    }
  },
  mutations: {
    /*
    setHighlightRange(state, range) {
      state.highlightRange = range;
    },
    */
  },
  plugins: [vuexLocal.plugin],

})

export default store;
