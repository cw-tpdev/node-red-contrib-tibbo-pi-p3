module.exports = function (RED) {
    "use strict";

    // TP Buzzer

    var TpCommon = require('./tpCommon');

    function TPC_BuzzerOutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tpcBuzzer", node);

        // Launch python
        tc.execPy([config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();
    }
    RED.nodes.registerType("tp-buzzer out", TPC_BuzzerOutNode);
}
