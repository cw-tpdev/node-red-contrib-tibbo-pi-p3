module.exports = function (RED) {
    "use strict";

    // TP LED 

    var TpCommon = require('./tpCommon');

    function TPC_LedOutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tpcLed", node);

        // Launch python
        tc.execPy([config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();

    }
    RED.nodes.registerType("tp-LED out", TPC_LedOutNode);
}
