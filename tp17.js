module.exports = function (RED) {
    "use strict";

    // #17 Three PWMs with power outputs

    var TpCommon = require('./tpCommon');

    function TP_17_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp17_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();
    }
    RED.nodes.registerType("Tibbit-#17 out", TP_17_OutNode);

}
