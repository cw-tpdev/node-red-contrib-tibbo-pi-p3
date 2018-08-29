module.exports = function (RED) {
    "use strict";

    // #57 FPGA Tibbit

    var TpCommon = require('./tpCommon');

    function TP_57_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp57_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();

    }
    RED.nodes.registerType("Tibbit-#57 out", TP_57_OutNode);
}
