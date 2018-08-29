module.exports = function (RED) {
    "use strict";

    // #23 Isolated PoE power supply, 5V output

    var TpCommon = require('./tpCommon');

    function TP_23_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp23_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();
    }
    RED.nodes.registerType("Tibbit-#23 out", TP_23_OutNode);
}
