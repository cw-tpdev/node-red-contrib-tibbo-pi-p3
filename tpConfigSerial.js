module.exports = function (RED) {
    "use strict";

    // Config - Serial

    function TP_Config_SerialNode(n) {
        RED.nodes.createNode(this, n);

        this.serialName = n.serialName;
        this.hardwareFlow = n.hardwareFlow;
        this.seriBaudRate = n.seriBaudRate;
        this.seriDataBits = n.seriDataBits;
        this.seriParity = n.seriParity;
        this.seriStartBits = n.seriStartBits;
        this.seriStopBits = n.seriStopBits;
        this.seriSplitInput = n.seriSplitInput;
        this.seriOnTheCharactor = n.seriOnTheCharactor;
        this.seriAfterATimeoutOf = n.seriAfterATimeoutOf;
        this.seriIntoFixedLengthOf = n.seriIntoFixedLengthOf;

    }
    RED.nodes.registerType("tp-config-serial", TP_Config_SerialNode);
}