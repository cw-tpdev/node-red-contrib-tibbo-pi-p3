module.exports = function (RED) {
    "use strict";

    // #12 Low-power +15/-15V power supply, 5V input

    var TpCommon = require('./tpCommon');

    function TP_12_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp12_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();
    }
    RED.nodes.registerType("Tibbit-#12 out", TP_12_OutNode);
}
