module.exports = function (RED) {
    "use strict";

    // #14 Four-channel DAC

    var TpCommon = require('./tpCommon');

    function TP_14_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp14_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();
    }
    RED.nodes.registerType("Tibbit-#14 out", TP_14_OutNode);

}
