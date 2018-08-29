module.exports = function (RED) {
    "use strict";

    // #16 Three PWMs with open collector outputs

    var TpCommon = require('./tpCommon');

    function TP_16_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp16_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();
    }
    RED.nodes.registerType("Tibbit-#16 out", TP_16_OutNode);

}
